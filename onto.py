import json,random,string
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, Literal
import argparse
import os
from rdflib import URIRef

# === Define shared 'has_field' superproperty ===
# has_field = PlatformPrefix.has_field
# g.add((has_field, RDF.type, OWL.ObjectProperty))
# g.add((has_field, RDFS.label, Literal("has_field")))

# === JSON type to XSD mapping ===
type_map = {
    "string": XSD.string,
    "integer": XSD.integer,
    "boolean": XSD.boolean,
    "number": XSD.decimal
}

# Reverse map for finding string representation from XSD URI
xsd_to_str_map = {v: k for k, v in type_map.items()}

class Ontology():

    def __init__(self, existing_ontology_file, catalog_file, output_ontology_file, platform, tap):
        self.EXISTING_TTL = existing_ontology_file
        self.SCHEMA_JSON = catalog_file
        self.OUTPUT_TTL = output_ontology_file
        self.PLATFORM = platform
        self.PLATFORM_PREFIX = self.PLATFORM.lower()
        self.TAP = tap

        temp_platform = self.PLATFORM.replace(" ", "_").replace("-", "_")
        parts = temp_platform.split('_')
        # Keep the first part as is, capitalize the first letter of subsequent parts, and join
        # Join parts without changing case initially
        joined_parts = "".join(parts)
        # Capitalize the first letter and make the rest lowercase
        platform_prefix_uri_formatted = joined_parts.capitalize()

        self.PLATFORM_URI = f"https://www.cohesyve.com/ontologies/Platforms/{platform_prefix_uri_formatted}#"

        # === Load Ontology & JSON ===
        self.g = Graph()
        self.g.parse(self.EXISTING_TTL, format="turtle")

        # === Define Namespace for New Platform ===
        self.BasePrefix = Namespace("https://www.cohesyve.com/ontologies/combined#")
        self.PlatformPrefix = Namespace(self.PLATFORM_URI)
        self.g.bind("", self.BasePrefix)
        self.g.bind(self.PLATFORM_PREFIX, self.PlatformPrefix)

        # === Find Subclasses of a Specific Class ===
        # Import URIRef if not already imported at the top

        # Define the target class URI
        target_class_uri = URIRef("https://www.cohesyve.com/ontologies/combined#maduz-holot-kogit-sojal")

        # Find resources that are subclasses of the target class
        subclasses = list(self.g.subjects(predicate=RDFS.subClassOf, object=target_class_uri))

        # === Ask user to choose a subclass ===
        self.selected_parent_platform_class_uri = None
        if subclasses:
            print("Found the following platform categories:")
            for i, subclass in enumerate(subclasses):
            # Attempt to get a label for better display, fallback to URI fragment
                label = self.g.value(subclass, RDFS.label)
                if not label:
                    label = subclass.split('#')[-1] if '#' in subclass else subclass.split('/')[-1]
                    
                print(f"  {i + 1}: {label}")

            print(f"  {len(subclasses) + 1}: Create a new category")

            while self.selected_parent_platform_class_uri is None:
                try:
                    choice = input("Enter the number of the category you want to add this platform to: ")
                    choice_index = int(choice) - 1

                    # Use the new platform prefix with the random slug
                    random_id = self.random_slug()
                    self.new_platform_class_uri = self.PlatformPrefix[random_id]
                
                    if 0 <= choice_index < len(subclasses):
                        self.selected_parent_platform_class_uri = subclasses[choice_index]
                        print(f"Using {self.g.value(self.selected_parent_platform_class_uri, RDFS.label) or self.selected_parent_platform_class_uri} as the parent class.")
                        break
                    elif choice_index == len(subclasses):
                        # Create a new category
                        new_category_name = input("\nEnter the name for the new category: ")
                        new_category_uri = self.BasePrefix[self.random_slug()]
                        self.g.add((new_category_uri, RDF.type, OWL.Class))
                        self.g.add((new_category_uri, RDFS.label, Literal(new_category_name + "Platform", lang="en")))
                        self.g.add((new_category_uri, RDFS.subClassOf, target_class_uri))
                        print(f"Created new category: {new_category_name} with URI: {new_category_uri}")
                        self.selected_parent_platform_class_uri = new_category_uri
                        break
                    else:
                        print("Invalid number. Please choose from the list.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            else:
                print(f"No subclasses found for {target_class_uri}. Cannot proceed with subclass selection.")
                # Handle this case as needed, e.g., exit or use a default
                # For now, self.parent_class_uri remains None
            
            print(f"Creating new platform class URI: {self.new_platform_class_uri}")

            # Add the new platform class as a subclass of the selected parent
            self.g.add((self.new_platform_class_uri, RDF.type, OWL.Class))
            self.g.add((self.new_platform_class_uri, RDFS.subClassOf, self.selected_parent_platform_class_uri))
            self.g.add((self.new_platform_class_uri, RDFS.label, Literal(f"{self.PLATFORM}", lang="en")))

            print(f"Added {self.new_platform_class_uri} as a subclass of {self.selected_parent_platform_class_uri}")
    
    def ontology_initialization(self, class_name):
        # create a platform class

        # create a main class
        random_id = self.random_slug()
        class_uri = self.PlatformPrefix[random_id]
        self.g.add((class_uri, RDF.type, OWL.Class))
        self.g.add((class_uri, RDFS.label, Literal(class_name+"PlatformField", lang="en")))

        # create the main property

        random_prop_id = self.random_slug()
        prop_uri = self.PlatformPrefix[random_prop_id]
        self.g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.g.add((prop_uri, RDFS.label, Literal(class_name + "Property", lang="en")))
        self.g.add((prop_uri, RDFS.domain, class_uri))  

        # Define and add the object property for the relationship
        relationship_prop_uri = self.PlatformPrefix[self.random_slug()]
        self.g.add((relationship_prop_uri, RDF.type, OWL.ObjectProperty))
        # Use the dynamic platform name for the label
        relationship_label = f"{self.PLATFORM}Relationship" 
        self.g.add((relationship_prop_uri, RDFS.label, Literal(relationship_label, lang="en")))
        # Optionally define domain and range for clarity
        self.g.add((relationship_prop_uri, RDFS.domain, self.new_platform_class_uri))
        self.g.add((relationship_prop_uri, RDFS.range, class_uri))

        # Add the triple linking the new platform class to the main class via the new object property
        # self.g.add((self.new_platform_class_uri, relationship_prop_uri, class_uri))

        self.main_class_uri = class_uri
        self.main_property_uri = prop_uri
        self.main_relationship_uri = relationship_prop_uri

        return class_uri, prop_uri, relationship_prop_uri

    def random_slug(self, num_parts=4, part_length=5):
        return "-".join(
            "".join(random.choices(string.ascii_lowercase, k=part_length))
            for _ in range(num_parts)
        )
    
    def string_naming(self, input_str):
        # if input_str != self.PLATFORM and input_str.endswith('s'):
        #     input_str = input_str[:-1]
        parts = input_str.split('_')
        # Capitalize the first letter of each part after the first one
        camel_case_parts = [parts[0]] + [part.capitalize() for part in parts[1:]]
        # Join the parts
        input_str = "".join(camel_case_parts)
        # Capitalize the first letter of the entire string
        if input_str:
             input_str = input_str[0].upper() + input_str[1:]
        return input_str

    def create_class_property(self, label):
        random_id = self.random_slug()
        class_uri = self.PlatformPrefix[random_id]
        self.g.add((class_uri, RDFS.label, Literal(label, lang="en")))
        self.g.add((class_uri, RDF.type, OWL.Class))
        self.g.add((class_uri, RDFS.isDefinedBy, Literal(label)))
        self.g.add((class_uri, RDFS.subClassOf, self.main_class_uri))

        # create the property of that class
        random_prop_id = self.random_slug()
        prop_uri = self.PlatformPrefix[random_prop_id]
        self.g.add((prop_uri, RDF.type, OWL.DatatypeProperty)) # Keep as DatatypeProperty for associating data fields
        self.g.add((prop_uri, RDFS.label, Literal(label + "Property", lang="en")))
        self.g.add((prop_uri, RDFS.domain, class_uri))
        self.g.add((prop_uri, RDFS.subPropertyOf, self.main_property_uri))

        return class_uri, prop_uri

    def construct_nested_sql_query(self, parent_sql_table_name, array_prop_name, item_schema, parent_key_properties):
        """Generates SQL query specifically for unnesting an array property."""
        select_clauses = []
        table_alias = "t"
        safe_prop_name_for_alias = ''.join(c if c.isalnum() else '_' for c in array_prop_name)
        array_alias = f"unnested_{safe_prop_name_for_alias}"

        # Select parent key properties
        for pk in parent_key_properties:
            quoted_pk_alias = f"`Parent_{pk}`"
            select_clauses.append(f"{table_alias}.`{pk}` AS {quoted_pk_alias}")

        # Select properties from the unnested item
        item_types = item_schema.get("type", [])
        if not isinstance(item_types, list):
            item_types = [item_types]
        clean_item_types = [t for t in item_types if t != "null"]
        primary_item_type = clean_item_types[0] if clean_item_types else "string"

        if primary_item_type == "object":
            item_properties = item_schema.get("properties", {})
            if not item_properties:
                select_clauses.append(f"SAFE_CAST({array_alias} AS STRING) AS `{array_prop_name}_object_value`")
            else:
                for sub_prop_name, sub_prop_details in item_properties.items():
                    quoted_alias = f"`{sub_prop_name}`"
                    select_clauses.append(f"SAFE_CAST(JSON_EXTRACT_SCALAR({array_alias}, '$.{sub_prop_name}') AS STRING) AS {quoted_alias}")
        else:
            quoted_alias = f"`{array_prop_name}_value`"
            select_clauses.append(f"SAFE_CAST({array_alias} AS STRING) AS {quoted_alias}")

        # Add _time_loaded from parent
        select_clauses.append(f"{table_alias}._time_loaded")

        select_statement = "SELECT\n  " + ",\n  ".join(list(dict.fromkeys(select_clauses)))
        from_statement = f"FROM\n  `cohesyve-us.#database_id.{self.TAP}__{parent_sql_table_name}` AS {table_alias}"
        unnest_join = f"LEFT JOIN UNNEST(COALESCE(JSON_EXTRACT_ARRAY(REPLACE(REPLACE({table_alias}.`{array_prop_name}`, 'True', 'true'), 'False', 'false')), [])) AS {array_alias}"
        where_statement = f"WHERE date({table_alias}._time_loaded) >= date('#cutoff_timestamp')"

        full_query = f"{select_statement}\n{from_statement}\n{unnest_join}\n{where_statement}"
        return full_query

    def process_array_property(self, parent_class_uri, parent_datatype_property_uri, parent_class_label, parent_sql_table_name, prop_name, prop_details, schema_data):
        """
        Handles array properties recursively by creating a new class, properties, SQL query,
        and equivalentProperty links. Processes nested arrays within objects.
        """
        item_schema = prop_details.get("items", {})
        if not item_schema:
            print(f"Warning: Array property '{prop_name}' in '{parent_class_label}' has no item schema defined. Skipping.")
            return

        # --- Create Class and Properties for the Array Items ---
        # Use a more descriptive label incorporating the parent and property name
        nested_class_label_base = f"{parent_class_label}{self.string_naming(prop_name)}Item" # Use string_naming for consistency
        nested_class_label = nested_class_label_base
        # Ensure uniqueness if the same array structure appears elsewhere (optional, depends on desired ontology structure)
        # nested_class_label = f"{parent_class_label}_{prop_name}_Items" # Alternative naming

        nested_class_uri = self.PlatformPrefix[self.random_slug()]
        self.g.add((nested_class_uri, RDF.type, OWL.Class))
        self.g.add((nested_class_uri, RDFS.label, Literal(nested_class_label, lang="en")))
        # Link nested class back to the main platform-specific field class
        self.g.add((nested_class_uri, RDFS.subClassOf, self.main_class_uri)) # All fields/items subclass the main field type

        # Datatype property for holding the fields of the items in this array
        nested_prop_uri = self.PlatformPrefix[self.random_slug()]
        self.g.add((nested_prop_uri, RDF.type, OWL.DatatypeProperty))
        self.g.add((nested_prop_uri, RDFS.label, Literal(f"{nested_class_label}Property", lang="en")))
        self.g.add((nested_prop_uri, RDFS.domain, nested_class_uri))
        # Link this property back to the main platform-specific property
        self.g.add((nested_prop_uri, RDFS.subPropertyOf, self.main_property_uri)) # All properties subclass the main property

        # Object property linking the parent class to this nested item class
        object_prop_label = f"has{self.string_naming(prop_name)}Item" # Use string_naming
        object_prop_uri = self.PlatformPrefix[self.random_slug()]
        self.g.add((object_prop_uri, RDF.type, OWL.ObjectProperty))
        self.g.add((object_prop_uri, RDFS.label, Literal(object_prop_label, lang="en")))
        self.g.add((object_prop_uri, RDFS.domain, parent_class_uri)) # Domain is the class containing the array
        self.g.add((object_prop_uri, RDFS.range, nested_class_uri)) # Range is the new class for array items
        # Link this relationship back to the main platform relationship property
        self.g.add((object_prop_uri, RDFS.subPropertyOf, self.main_relationship_uri))

        # --- Process Item Schema (Recursive Step) ---
        item_types = item_schema.get("type", [])
        if not isinstance(item_types, list):
            item_types = [item_types]
        clean_item_types = [t for t in item_types if t != "null"]
        primary_item_type = clean_item_types[0] if clean_item_types else "string" # Default to string if no type found

        if primary_item_type == "object":
            item_properties = item_schema.get("properties", {})
            if not item_properties:
                 print(f"Warning: Array property '{prop_name}' contains objects with no properties defined in schema. Creating a placeholder value property.")
                 # Create a placeholder if object has no defined properties
                 self.create_subproperty(nested_prop_uri, f"{prop_name}_object_value", "string", is_primary_key=False)
            else:
                for sub_prop_name, sub_prop_details in item_properties.items():
                    sub_types = sub_prop_details.get("type", [])
                    if not isinstance(sub_types, list):
                        sub_types = [sub_types]
                    clean_sub_types = [st for st in sub_types if st != "null"]
                    primary_sub_type = clean_sub_types[0] if clean_sub_types else "string"

                    # === Recursive Call for Nested Arrays ===
                    if primary_sub_type == "array":
                        print(f"      - Found nested array '{sub_prop_name}' within '{prop_name}'. Processing recursively.")
                        # Note: The SQL generated by the recursive call might need adjustments for >1 level nesting,
                        # as construct_nested_sql_query assumes unnesting from the original parent_sql_table_name.
                        self.process_array_property(
                            nested_class_uri,           # Parent class is the one we just created
                            nested_prop_uri,            # Parent property is the one we just created
                            nested_class_label,         # Parent label is the one we just created
                            parent_sql_table_name,      # Base table for SQL remains the original parent
                            sub_prop_name,              # Current property name is the sub-property's name
                            sub_prop_details,           # Current property details are the sub-property's
                            schema_data                 # Pass original schema_data for key_properties lookup
                        )
                    # === Handle Nested Objects (Non-Array) ===
                    # elif primary_sub_type == "object":
                        # Decide how to handle nested objects that are *not* arrays.
                        # Option 1: Flatten - Create subproperties like prop_subprop
                        # Option 2: Create another nested class (similar to array handling but without recursion here)
                        # Option 3: Skip/Placeholder - Create a single property representing the object as string/JSON
                        # Current implementation (implicitly via create_subproperty) flattens slightly
                        # by creating subproperties directly under the current nested_prop_uri.
                        # For deeper structures or explicit object classes, more logic would be needed here.
                        # print(f"      - Processing nested object property '{sub_prop_name}' within '{prop_name}'.")
                        # self.create_subproperty(nested_prop_uri, sub_prop_name, primary_sub_type, is_primary_key=False)
                        # If choosing Option 1 (flattening further):
                        # nested_object_props = sub_prop_details.get("properties", {})
                        # for n_obj_prop, n_obj_details in nested_object_props.items():
                        #    # ... get type ...
                        #    self.create_subproperty(nested_prop_uri, f"{sub_prop_name}_{n_obj_prop}", n_obj_type, False)
                        # Pass - current logic handles basic object flattening via SQL JSON extraction in construct_class_sql_query
                        # and simple subproperty creation below for non-array/non-object types.
                        # Let's create the simple subproperty for now.
                        # self.create_subproperty(nested_prop_uri, sub_prop_name, primary_sub_type, is_primary_key=False)
                        # Actually, let construct_nested_sql_query handle object extraction for now. Don't create ontology props for nested objects here.
                        # Let's refine: create subproperties for simple types within the object.
                        # self.create_subproperty(nested_prop_uri, sub_prop_name, primary_sub_type, is_primary_key=False)
                        # Let's stick to creating subproperties for the direct fields of the object.
                        self.create_subproperty(nested_prop_uri, sub_prop_name, primary_sub_type, is_primary_key=False)

                    # === Handle Simple Types ===
                    else:
                        self.create_subproperty(nested_prop_uri, sub_prop_name, primary_sub_type, is_primary_key=False)

        # --- Handle Simple Item Types (e.g., array of strings) ---
        else:
            # If the array items are not objects (e.g., ["apple", "banana"])
            # Create a single property to hold the value of the item
            value_prop_label = f"{self.string_naming(prop_name)}Value" # More specific label
            self.create_subproperty(nested_prop_uri, value_prop_label, primary_item_type, is_primary_key=False)

        # --- Generate SQL Query for this level of unnesting ---
        # Note: This query unnests THIS array from its direct parent table.
        # Deeper nested arrays handled by recursive calls will generate their own queries,
        # potentially requiring manual combination or CTEs for a single, multi-level unnesting query.
        parent_key_properties = schema_data.get("key_properties", [])
        nested_sql_query = self.construct_nested_sql_query(parent_sql_table_name, prop_name, item_schema, parent_key_properties)
        query_uri = self.BasePrefix["query"]
        self.g.add((nested_class_uri, query_uri, Literal(nested_sql_query, datatype=XSD.string)))

        # --- Add equivalentProperty links for parent primary keys ---
        # This links the parent's PK property to the corresponding 'Parent_PK' property created in the nested class
        # This helps establish the foreign key relationship in the ontology.
        if parent_key_properties: # Only proceed if parent has defined key properties
            for pk in parent_key_properties:
                parent_pk_prop_uri = None
                # Find the parent's specific property URI for this key by searching its subproperties
                for parent_sub_prop in self.g.subjects(predicate=RDFS.subPropertyOf, object=parent_datatype_property_uri):
                    # Check if this subproperty's RDFS.isDefinedBy matches the primary key name
                    defined_by_label = self.g.value(subject=parent_sub_prop, predicate=RDFS.isDefinedBy)
                    if defined_by_label == Literal(pk):
                        parent_pk_prop_uri = parent_sub_prop
                        break # Found it

                if parent_pk_prop_uri:
                    # Determine the datatype of the parent key to use for the nested key
                    parent_pk_datatype_uri = self.g.value(subject=parent_pk_prop_uri, predicate=RDFS.range)
                    parent_pk_datatype_str = xsd_to_str_map.get(parent_pk_datatype_uri, "string") # Default to string

                    # Create the corresponding property in the nested class (acts as FK)
                    # Use the naming convention matching the SQL alias from construct_nested_sql_query
                    nested_pk_label = f"Parent_{pk}"
                    nested_pk_prop_uri = self.create_subproperty(
                        nested_prop_uri,        # Parent property is the main datatype property of the nested class
                        nested_pk_label,        # Label matches SQL alias convention
                        parent_pk_datatype_str, # Use the same datatype as the parent PK
                        is_primary_key=False    # It's a foreign key conceptually, not the PK of the nested item itself
                    )

                    # Add the equivalentProperty link
                    self.g.add((nested_pk_prop_uri, OWL.equivalentProperty, parent_pk_prop_uri))
                    print(f"      - Added equivalentProperty link for '{pk}' between <{nested_pk_prop_uri.n3()}> and <{parent_pk_prop_uri.n3()}>")
                else:
                    # This might happen if the key_properties listed in JSON don't match properties found in the schema block
                    print(f"Warning: Could not find parent property URI for primary key '{pk}' defined by '{pk}' under property <{parent_datatype_property_uri.n3()}>. Cannot add equivalentProperty link.")
        # --- End equivalentProperty links ---

        print(f"    - Processed array property '{prop_name}' into new class <{nested_class_uri.n3()}>")


    def construct_class_sql_query(self, class_name, properties, schema_data):
        select_clauses_main = []
        from_clause_parts = []
        table_alias = "t"
        table_name_formatted = class_name.lower().replace('platformfield', '').replace('property', '')
        from_clause_parts.append(f"`cohesyve-us.#database_id.{self.TAP}__{table_name_formatted}` AS {table_alias}")

        for prop_name, prop_details in properties.items():
            original_prop_name = prop_name
            quoted_prop_alias = f"`{prop_name}`"

            types = prop_details.get("type", [])
            if not isinstance(types, list):
                types = [types]
            clean_types = [t for t in types if t != "null"]
            primary_type = clean_types[0] if clean_types else "string"

            if primary_type == "array":
                continue
            elif primary_type == "object":
                object_properties = prop_details.get("properties", {})
                for sub_prop_name, sub_prop_details in object_properties.items():
                    quoted_alias = f"`{original_prop_name}_{sub_prop_name}`"
                    select_clauses_main.append(f"SAFE_CAST(JSON_EXTRACT_SCALAR({table_alias}.`{original_prop_name}`, '$.{sub_prop_name}') AS STRING) AS {quoted_alias}")
            else:
                select_clauses_main.append(f"{table_alias}.`{original_prop_name}` AS {quoted_prop_alias}")

        has_time_loaded = '_time_loaded' in properties
        if not has_time_loaded:
            select_clauses_main.append(f"{table_alias}._time_loaded")
            has_time_loaded = True

        all_select_clauses = list(dict.fromkeys(select_clauses_main))

        if not all_select_clauses:
            key_props = [p for p, d in properties.items() if p in schema_data.get("key_properties", [])]
            if key_props:
                for pk in key_props:
                    all_select_clauses.append(f"{table_alias}.`{pk}` AS `{pk}`")
                if not has_time_loaded:
                    all_select_clauses.append(f"{table_alias}._time_loaded")
                    has_time_loaded = True
            else:
                all_select_clauses.append("1")

        select_statement = "SELECT\n  " + ",\n  ".join(all_select_clauses)
        from_statement = "FROM\n  " + "\n  ".join(from_clause_parts)
        where_statement = f"WHERE date({table_alias}._time_loaded) >= date('#cutoff_timestamp')" if has_time_loaded else ""

        full_query = f"{select_statement}\n{from_statement}"
        if where_statement:
            full_query += f"\n{where_statement}"

        return full_query

    def create_subproperty(self, parent_class_uri, prop_name, datatype, is_primary_key=False):
        random_id = self.random_slug()
        prop_uri = self.PlatformPrefix[random_id]
        self.g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.g.add((prop_uri, RDFS.subPropertyOf, parent_class_uri))
        self.g.add((prop_uri, RDFS.label, Literal(prop_name)))
        self.g.add((prop_uri, RDFS.range, type_map.get(datatype, XSD.string)))
        self.g.add((prop_uri, RDFS.isDefinedBy, Literal(prop_name)))

        if is_primary_key:
            is_primary_key_uri = self.BasePrefix["isPrimaryKey"]
            self.g.add((prop_uri, is_primary_key_uri, Literal("true", datatype=XSD.boolean)))

        return prop_uri

    def process_schema(self, class_name, schema_data, class_uri, property_uri, relationship_uri):
        original_class_name = schema_data.get("stream")
        table_name_formatted = original_class_name.lower()

        current_class, current_datatype_property = self.create_class_property(class_name)
        object_schema = schema_data.get("schema", {})
        properties = object_schema.get('properties', {})
        if not properties:
            print(f"Warning: No properties found for stream '{original_class_name}'. Skipping property processing.")
            return current_datatype_property

        for prop_name, prop_details in properties.items():
            types = prop_details.get("type", [])
            if not isinstance(types, list):
                types = [types]

            clean_types = [t for t in types if t != "null"]
            primary_type = clean_types[0] if clean_types else "string"

            is_primary_key = prop_name in schema_data.get("key_properties", [])

            if primary_type == "array":
                self.process_array_property(current_class, current_datatype_property, class_name, table_name_formatted, prop_name, prop_details, schema_data)
            elif primary_type == "object":
                # Optionally handle nested objects directly if needed, or skip like arrays
                # For now, skipping direct processing of object properties here, assuming they might be handled if nested within arrays or need separate logic
                print(f"  - Skipping direct processing for object property '{prop_name}' in '{class_name}'. Nested properties defined via subProperty.")
                # If you need to create subproperties for nested object fields:
                # object_props = prop_details.get("properties", {})
                # for sub_prop, sub_details in object_props.items():
                #     sub_types = sub_details.get("type", [])
                #     # ... process sub_types ...
                #     self.create_subproperty(current_datatype_property, f"{prop_name}_{sub_prop}", sub_primary_type, is_primary_key=False) # Adjust naming as needed
                pass # Keep pass if skipping direct processing here
            else:
                self.create_subproperty(current_datatype_property, prop_name, primary_type, is_primary_key)

        class_sql_query = self.construct_class_sql_query(class_name, properties, schema_data)

        query_uri = self.BasePrefix["query"]
        self.g.add((current_class, query_uri, Literal(class_sql_query, datatype=XSD.string)))

        return current_datatype_property

def list_files(extension):
    """Lists files with a specific extension in the current directory."""
    files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith(extension)]
    return files

def get_file_input(prompt, extension):
    """Gets file input, allowing selection from the current directory."""
    print(f"\n{prompt}")
    files = list_files(extension)
    if files:
        print("Files in current directory:")
        for i, f in enumerate(files):
            print(f"  {i + 1}: {f}")
        print("Enter the number to select a file, or type the full path:")
    else:
        print("No relevant files found in the current directory. Please enter the full path:")

    while True:
        user_input = input("> ")
        try:
            selection_index = int(user_input) - 1
            if 0 <= selection_index < len(files):
                return os.path.join(os.getcwd(), files[selection_index])
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            if os.path.exists(user_input):
                if not os.path.dirname(user_input) and os.path.exists(os.path.join(os.getcwd(), user_input)):
                    return os.path.join(os.getcwd(), user_input)
                return user_input
            elif not os.path.dirname(user_input) and extension in user_input:
                print(f"Warning: File '{user_input}' not found, but assuming it's intended for the current directory.")
                return os.path.join(os.getcwd(), user_input)
            elif os.path.dirname(user_input):
                print(f"Error: Path '{user_input}' not found. Please enter a valid path or select a number.")
            else:
                print(f"Assuming '{user_input}' is a filename for the current directory.")
                return os.path.join(os.getcwd(), user_input)

def get_output_file_input(default_extension=".ttl"):
    """Gets the output file path, defaulting to the current directory."""
    user_input = input("\nEnter the desired output filename (e.g., 'output.ttl') or a full path: ")
    if not os.path.dirname(user_input):
        if not user_input.endswith(default_extension):
            user_input += default_extension
        return os.path.join(os.getcwd(), user_input)
    else:
        if not os.path.basename(user_input).endswith(default_extension):
            if '.' not in os.path.basename(user_input):
                print(f"Warning: Output path '{user_input}' looks like a directory. Saving as '{os.path.join(user_input, 'output' + default_extension)}'")
                return user_input + default_extension
            elif not user_input.endswith(default_extension):
                print(f"Warning: Output file '{user_input}' does not have the expected '{default_extension}' extension.")
                return user_input
        return user_input

def main():
    existing_ontology_file = get_file_input("Enter the path to the existing base ontology file (.ttl):", ".ttl")
    catalog_file = get_file_input("Enter the path to the schema catalog file (.json):", ".json")
    output_ontology_file = get_output_file_input()
    platform_name = input("\nEnter the name of the platform (e.g., 'Razorpay'): ")
    tap_name = input("\nEnter the name of the tap (e.g., 'razorpay'): ")

    print("\n--- Configuration ---")
    print(f"Base Ontology: {existing_ontology_file}")
    print(f"Catalog File:  {catalog_file}")
    print(f"Output File:   {output_ontology_file}")
    print(f"Platform Name: {platform_name}")
    print("---------------------\n")

    if not os.path.isfile(existing_ontology_file):
        print(f"Error: Base ontology file not found at '{existing_ontology_file}'")
        return
    if not os.path.isfile(catalog_file):
        print(f"Error: Catalog file not found at '{catalog_file}'")
        return

    try:
        working_ontology = Ontology(existing_ontology_file, catalog_file, output_ontology_file, platform_name, tap_name)

        with open(catalog_file, "r") as f:
            schema_data = json.load(f)

        platform_name_formatted = working_ontology.string_naming(platform_name)
        class_uri, property_uri, relationship_uri = working_ontology.ontology_initialization(platform_name_formatted)

        streams = schema_data.get('streams', [])
        if not streams:
            print("Warning: No 'streams' found in the catalog file.")

        for single_schema in streams:
            root_class_name = single_schema.get("stream")
            if not root_class_name:
                print("Warning: Skipping stream with missing 'stream' key.")
                continue

            print(f"Processing stream: {root_class_name}...")
            root_class_name_formatted = working_ontology.string_naming(root_class_name)
            working_ontology.process_schema(root_class_name_formatted, single_schema, class_uri, property_uri, relationship_uri)

        working_ontology.g.serialize(destination=output_ontology_file, format="turtle")
        print(f"\nOntology successfully generated and saved to {output_ontology_file}")

    except FileNotFoundError as e:
        print(f"Error loading file: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON catalog file '{catalog_file}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
