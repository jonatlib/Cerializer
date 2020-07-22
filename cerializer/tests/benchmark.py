import timeit
from typing import List, Union, Dict, Hashable, Any, Tuple

import texttable
import yaml

import cerializer.cerializer_handler
import cerializer.utils


SCHEMA_ROOT = '/Users/matejmicek/PycharmProjects/schema_root'
SCHEMA_ROOT = '/Users/matejmicek/PycharmProjects/Cerializer/cerializer/tests/schemata'


def benchmark_schema_serialize(
	schema_root: str,
	schema_favro: Union[Dict[Hashable, Any], list, None],
	path: str,
	count: int,
	schema_name: str,
	schema_identifier: str,
) -> Tuple:
	'''
	Helper function. This should not be used on its own. Use benchmark() instead.
	'''
	setup = f'''
import benchmark
import fastavro
import json
import io
import json
import yaml
import cerializer.compiler
# fixes a Timeit NameError 'mappingproxy'
from types import MappingProxyType as mappingproxy


schema_favro = {schema_favro}
data = yaml.unsafe_load(open('{path}' + 'example.yaml'))
parsed_schema = fastavro.parse_schema(schema_favro)
output = io.BytesIO()

import cerializer.cerializer_handler as c
import datetime
from decimal import Decimal
from uuid import UUID
import json

buff = io.BytesIO()

x = c.Cerializer(['{schema_root}']).code['{schema_identifier}']['serialize']
	'''

	score_string_cerializer = timeit.timeit(stmt = 'x(data, buff)', setup = setup, number = count)
	score_fastavro_serialize = timeit.timeit(
		stmt = 'fastavro.schemaless_writer(output, parsed_schema, data)',
		setup = setup,
		number = count,
	)

	try:
		score_json_serialize = timeit.timeit(stmt = 'json.dumps(data)', setup = setup, number = count)
	except TypeError:
		print(  # dumb_style_checker:disable = print-statement
			f'Schema = {schema_name} has elements not supported by JSON.'
		)
		score_json_serialize = 666 * score_string_cerializer

	return (score_string_cerializer, score_fastavro_serialize, score_json_serialize)


def benchmark_schema_deserialize(
	schema_root: str,
	schema_favro: Union[Dict[Hashable, Any], list, None],
	path: str,
	count: int,
	schema_name: str,
	schema_identifier: str,
) -> Tuple:
	'''
	Helper function. This should not be used on its own. Use benchmark() instead.
	'''
	setup = f'''
import benchmark
import fastavro
import json
import io
import yaml
import cerializer.compiler
# fixes a Timeit NameError 'mappingproxy'
from types import MappingProxyType as mappingproxy


schema_favro = {schema_favro}
data = yaml.unsafe_load(open('{path}' + 'example.yaml'))
parsed_schema = fastavro.parse_schema(schema_favro)
serialized_data = io.BytesIO()

fastavro.schemaless_writer(serialized_data, parsed_schema, data)
serialized_data.seek(0)
import cerializer.cerializer_handler as c
import datetime
from decimal import Decimal
from uuid import UUID
try:
	json_data = json.dumps(data)
except: 
	json_data = None
x = c.Cerializer(['{schema_root}']).code['{schema_identifier}']['deserialize']
	'''

	score_string_cerializer = timeit.timeit(
		stmt = 'serialized_data.seek(0)\n' 'y = x(serialized_data)',
		setup = setup,
		number = count,
	)
	score_fastavro_serialize = timeit.timeit(
		stmt = 'serialized_data.seek(0)\n' 'y = fastavro.schemaless_reader(serialized_data, parsed_schema)',
		setup = setup,
		number = count,
	)

	try:
		score_json_deserialize = timeit.timeit(stmt = 'y = json.loads(json_data)', setup = setup, number = count)
	except TypeError:
		print(  # dumb_style_checker:disable = print-statement
			f'Schema = {schema_name} has elements not supported by JSON.'
		)
		score_json_deserialize = 666 * score_string_cerializer

	return (score_string_cerializer, score_fastavro_serialize, score_json_deserialize)


def benchmark(schema_root: str, count = 100000) -> str:
	'''
	Benchmarking function. Compares FastAvro, Cerializer and Json.
	In some cases, Json is not able to serialize given data. In such a case it is given an arbitrary score.
	'''
	schemata = list(cerializer.utils.iterate_over_schemata(schema_root))
	table_results_serialize: List[Tuple[Any, Any]] = []
	table_results_deserialize: List[Tuple[Any, Any]] = []
	table_results_roundtrip: List[Tuple[Any, Any]] = []
	for schema, version in schemata:
		SCHEMA_FILE = f'{schema_root}/messaging/{schema}/{version}/schema.yaml'
		SCHEMA_FAVRO = yaml.load(open(SCHEMA_FILE), Loader = yaml.Loader)
		result_deserialize = benchmark_schema_deserialize(
			schema_root = schema_root,
			path = f'{schema_root}/messaging/{schema}/{version}/',
			schema_favro = SCHEMA_FAVRO,
			count = count,
			schema_name = schema,
			schema_identifier = cerializer.cerializer_handler.get_schema_identifier('messaging', schema, version),
		)

		result_serialize = benchmark_schema_serialize(
			schema_root = schema_root,
			path = f'{schema_root}/messaging/{schema}/{version}/',
			schema_favro = SCHEMA_FAVRO,
			count = count,
			schema_name = schema,
			schema_identifier = cerializer.cerializer_handler.get_schema_identifier('messaging', schema, version),
		)

		table_results_serialize.append(
			(result_serialize[1] / result_serialize[0], result_serialize[2] / result_serialize[0])
		)
		table_results_deserialize.append(
			(result_deserialize[1] / result_deserialize[0], result_deserialize[2] / result_deserialize[0])
		)
		table_results_roundtrip.append(
			(
				(result_deserialize[1] + result_serialize[1]) / (result_deserialize[0] + result_serialize[0]),
				(result_deserialize[2] + result_serialize[2]) / (result_deserialize[0] + result_serialize[0]),
			)
		)

	names = [f'{schema[0]}:{str(schema[1])}' for schema in schemata]

	tables: List[str] = []

	for heading, results in (
		('serialize', table_results_serialize),
		('deserialize', table_results_deserialize),
		('roundtrip', table_results_roundtrip),
	):
		table = texttable.Texttable()
		table.header([heading + ' benchmark', 'FastAvro [x faster]', 'Json [x faster]'])
		fast_avro_score = [res[0] for res in results]
		json_score = [res[1] for res in results]
		for row in zip(names, fast_avro_score, json_score):
			table.add_row(row)
		tables.append(table.draw())
	return '\n\n\n'.join(tables)


print(benchmark(SCHEMA_ROOT, 100000))
