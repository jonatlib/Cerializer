import jinja2
import cerializer.schema_parser
import os



def dict_serialization(dictionary, buffer_name, relative_directory):
    return '\n'.join(dict_serialization_generator(
        dictionary = dictionary,
        prefix = '',
        buffer_name = buffer_name,
        relative_directory = relative_directory)
    )



def dict_serialization_generator(dictionary, prefix, buffer_name, relative_directory):
    for key, value in dictionary.items():
        _type = type(value)
        if _type is dict:
            yield from dict_serialization_generator(value, f'{prefix}[\'{key}\']', buffer_name, relative_directory)
        else:
            yield f'{relative_directory}.write_{value}({buffer_name}, data{prefix}[\'{key}\'])'



def render_schema(rendered_filename, schema):
    env = jinja2.Environment(
        loader = jinja2.FileSystemLoader(searchpath = 'cerializer/templates')
    )
    env.globals['serialization_code'] = cerializer.schema_parser.generate_serialization_code

    template = env.get_template('template.jinja2')
    rendered_template = template.render(schema = schema)
    output = open(os.path.join('cerializer', rendered_filename), 'w')
    output.write(rendered_template)
    output.close()


def update_schemata(schema_roots):
    for schema_root in schema_roots:
        schema_root = os.fsencode(schema_root)
        for namespace in os.listdir(schema_root):
            for schema_name in os.listdir(os.path.join(schema_root, namespace)):
                for version in os.listdir(os.path.join(schema_root, namespace, schema_name)):
                    schema_path = os.path.join(schema_root, namespace, schema_name, version, b'schema.yaml')
                    filename = f'{schema_name.decode()}_{version.decode()}.pyx'
                    code_path = os.path.join('cerializer_base', filename)
                    schema = cerializer.schema_parser.parse_schema_from_file(schema_path.decode())
                    render_schema(code_path, schema = schema)
    os.system('python setup.py build_ext --inplace')

update_schemata(['cerializer/tests/schemata'])