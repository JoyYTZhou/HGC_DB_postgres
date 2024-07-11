import csv
import asyncio
import asyncpg
import xml.etree.ElementTree as ET
import yaml
import sys
sys.path.append('../')
import os
import ast

async def load_mapping_from_csv(csv_file):
    mapping = {}
    with open(csv_file, mode='r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        for row in reader:
            xml_tag = row[0]
            try:
                db_columns = ast.literal_eval(row[1]) if row[1] else []  # Safely convert string representation of list to actual list
            except ValueError:
                db_columns = [row[1]]  # Handle single string without list
            table_name = row[2] if row[2] else None  # Handle NaN
            if table_name and db_columns:
                mapping[xml_tag] = (db_columns, table_name)
    return mapping

async def fetch_bp_name(conn):
    query = "SELECT bp_name FROM baseplate LIMIT 1"
    result = await conn.fetchval(query)
    return result

async def fetch_institution(conn, bp_name):
    query = """
        SELECT mi.institution
        FROM baseplate bp
        JOIN proto_assembly pa ON bp.proto_no = pa.proto_no
        JOIN module_info mi ON pa.module_no = mi.module_no
        WHERE bp.bp_name = $1
    """
    result = await conn.fetchval(query, bp_name)
    return result

async def fetch_value(conn, table, columns):
    if len(columns) == 1:
        query = f"SELECT {columns[0]} FROM {table} LIMIT 1"
        result = await conn.fetchval(query)
        return result
    elif len(columns) > 1:
        query = f"SELECT {', '.join(columns)} FROM {table} LIMIT 1"
        result = await conn.fetchrow(query)
        if result:
            return {col: result[col] for col in columns}
        else:
            return {col: None for col in columns}

async def insert_values_into_xml(xml_file, mapping, conn):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Fetch bp_name and institution
    bp_name = await fetch_bp_name(conn)
    institution = await fetch_institution(conn, bp_name)
    
    # Placeholder values to replace
    placeholders = {
        'ID': bp_name,
        'LOCATION': institution,
    }

    for xml_tag, info in mapping.items():
        columns = info[0]
        table = info[1]
        
        if xml_tag not in placeholders:
            if len(columns) == 2 and xml_tag in ['RUN_BEGIN_TIMESTAMP_', 'KIND_OF_PART']:
                # Special handling for combined columns
                value = await fetch_value(conn, table, columns)
                if xml_tag == 'RUN_BEGIN_TIMESTAMP_':
                    placeholders[xml_tag] = f"{value[columns[0]]}T{value[columns[1]]}"
                elif xml_tag == 'KIND_OF_PART':
                    placeholders[xml_tag] = f"{value[columns[0]]}_{value[columns[1]]}"
            else:
                value = await fetch_value(conn, table, columns)
                placeholders[xml_tag] = value if not isinstance(value, dict) else value

   # Insert values into XML by replacing placeholders
    for element in root.iter():
        if element.text:
            for xml_tag, value in placeholders.items():
                if isinstance(value, dict):
                    for col, val in value.items():
                        placeholder = f"{{{{ {col} }}}}"
                        if placeholder in element.text:
                            element.text = element.text.replace(placeholder, str(val) if val is not None else '')
                else:
                    placeholder_lower = f"{{{{ {xml_tag.lower()} }}}}"
                    placeholder_upper = f"{{{{ {xml_tag.upper()} }}}}"
                    placeholder = f"{{{{ {xml_tag} }}}}"
                    
                    if placeholder_lower in element.text:
                        element.text = element.text.replace(placeholder_lower, str(value) if value is not None else '')
                    if placeholder_upper in element.text:
                        element.text = element.text.replace(placeholder_upper, str(value) if value is not None else '')
                    if placeholder in element.text:
                        element.text = element.text.replace(placeholder, str(value) if value is not None else '')

    # Save the updated XML to the directory
    output_dir = 'converted_xml'
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, os.path.basename(xml_file))
    tree.write(output_file)
    print(f'Successfully created {output_file}')

async def main():
    # Load mapping
    mapping = await load_mapping_from_csv('../export/var_match_up/cond_upload.csv')## worked. 

    # Connect to PostgreSQL
    loc = '../dbase_info/'
    yaml_file = f'{loc}tables.yaml'
    db_params = {
        'database': yaml.safe_load(open(yaml_file, 'r'))['dbname'],
        'user': 'postgres',   
        # 'password': input('Set superuser password: '),
        'password': 'hgcal',
        'host': yaml.safe_load(open(yaml_file, 'r'))['db_hostname'],  
        'port': yaml.safe_load(open(yaml_file, 'r'))['port']        
    }

    # establish a connection with database
    conn = await asyncpg.connect(user=db_params['user'], 
                                password=db_params['password'], 
                                host=db_params['host'], 
                                database=db_params['database'],
                                port=db_params['port'])

    xml_path = '../export/template_examples/baseplates/cond_upload.xml'

    try:
        await insert_values_into_xml(xml_path, mapping, conn)
    finally:
        await conn.close()
if __name__ == '__main__':
    asyncio.run(main())