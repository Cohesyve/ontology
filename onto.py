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

class Ontology():

    def __init__(self, existing_ontology_file, catalog_file, output_ontology_file, platform):
        self.EXISTING_TTL = existing_ontology_file
        self.SCHEMA_JSON = catalog_file
        self.OUTPUT_TTL = output_ontology_file
        self.PLATFORM = platform
        self.PLATFORM_PREFIX = self.PLATFORM.lower()

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
            print("Found the following subclasses of the target class:")
            for i, subclass in enumerate(subclasses):
            # Attempt to get a label for better display, fallback to URI fragment
                label = self.g.value(subclass, RDFS.label)
                if not label:
                    label = subclass.split('#')[-1] if '#' in subclass else subclass.split('/')[-1]
                    
                print(f"  {i + 1}: {label}")

            while self.selected_parent_platform_class_uri is None:
                try:
                    choice = input("Enter the number of the subclass you want to use as the parent: ")
                    choice_index = int(choice) - 1
                    if 0 <= choice_index < len(subclasses):
                        self.selected_parent_platform_class_uri = subclasses[choice_index]
                        print(f"Using {self.g.value(self.selected_parent_platform_class_uri, RDFS.label) or self.selected_parent_platform_class_uri} as the parent class.")

                        # Use the new platform prefix with the random slug
                        random_id = self.random_slug()
                        self.new_platform_class_uri = self.PlatformPrefix[random_id]

                        print(f"Creating new platform class URI: {self.new_platform_class_uri}")

                        # Add the new platform class as a subclass of the selected parent
                        self.g.add((self.new_platform_class_uri, RDF.type, OWL.Class))
                        self.g.add((self.new_platform_class_uri, RDFS.subClassOf, self.selected_parent_platform_class_uri))
                        self.g.add((self.new_platform_class_uri, RDFS.label, Literal(f"{self.PLATFORM}", lang="en")))

                        print(f"Added {self.new_platform_class_uri} as a subclass of {self.selected_parent_platform_class_uri}")
                        break
                    else:
                        print("Invalid number. Please choose from the list.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            else:
                print(f"No subclasses found for {target_class_uri}. Cannot proceed with subclass selection.")
                # Handle this case as needed, e.g., exit or use a default
                # For now, self.parent_class_uri remains None
    
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

        return class_uri, prop_uri

    def random_slug(self, num_parts=4, part_length=5):
        return "-".join(
            "".join(random.choices(string.ascii_lowercase, k=part_length))
            for _ in range(num_parts)
        )
    
    def string_naming(self, input_str):
        if input_str != self.PLATFORM and input_str.endswith('s'):
            input_str = input_str[:-1]
        parts = input_str.split('_')
        # Capitalize the first letter of each part after the first one
        camel_case_parts = [parts[0]] + [part.capitalize() for part in parts[1:]]
        # Join the parts
        input_str = "".join(camel_case_parts)
        # Capitalize the first letter of the entire string
        if input_str:
             input_str = input_str[0].upper() + input_str[1:]
        return input_str

    def create_class_property(self, label, parent_class_name,parent_property_name):
        random_id = self.random_slug()
        class_uri = self.PlatformPrefix[random_id]
        # print(description,parent_class_name)
        self.g.add((class_uri, RDFS.label, Literal(label, lang="en")))
        self.g.add((class_uri, RDF.type, OWL.Class))
        self.g.add((class_uri, RDFS.isDefinedBy, Literal(label)))
        self.g.add((class_uri, RDFS.subClassOf, parent_class_name))

        # create the property of that class
        random_prop_id = self.random_slug()
        prop_uri = self.PlatformPrefix[random_prop_id]
        self.g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.g.add((prop_uri, RDFS.label, Literal(label + "Property", lang="en")))
        self.g.add((prop_uri, RDFS.subPropertyOf, parent_property_name))  
        self.g.add((prop_uri, RDFS.domain, class_uri))  

        return prop_uri


    def create_subproperty(self, parent_class_uri, prop_name, datatype, is_primary_key=False):
        random_id = self.random_slug()
        prop_uri = self.PlatformPrefix[random_id]
        self.g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        # g.add((prop_uri, RDFS.domain, parent_class_uri))
        self.g.add((prop_uri, RDFS.subPropertyOf, parent_class_uri))
        self.g.add((prop_uri, RDFS.label, Literal(prop_name)))
        self.g.add((prop_uri, RDFS.range, type_map.get(datatype, XSD.string)))
        self.g.add((prop_uri, RDFS.isDefinedBy, Literal(prop_name)))

        if is_primary_key:
            # Add custom annotation property isPrimaryKey :isPrimaryKey a owl:AnnotationProperty . with prefix @prefix : <https://www.cohesyve.com/ontologies/combined#> .
            is_primary_key_uri = self.BasePrefix["isPrimaryKey"]
            self.g.add((prop_uri, is_primary_key_uri, Literal("true", datatype=XSD.boolean)))

        return prop_uri

    def process_schema(self, class_name, schema_data,class_uri,property_uri):
        current_class = self.create_class_property(class_name, class_uri,property_uri)
        object_schema = schema_data.get("schema", {})
        properties = object_schema['properties']
        for prop_name, prop in properties.items():
            types = prop.get("type", [])
            if not isinstance(types, list):
                types = [types]

            # Remove null types, default to string if none found
            clean_types = [t for t in types if t != "null"]
            primary_type = clean_types[0] if clean_types else "string"

            # Check if the property is a primary key in object_schema['key_properties']
            is_primary_key = prop_name in schema_data.get("key_properties", [])

            self.create_subproperty(current_class, prop_name, primary_type, is_primary_key)

        return current_class

# 1st process add all the basic definitions Ex-Razorpay
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
            # Check if input is a number corresponding to a listed file
            selection_index = int(user_input) - 1
            if 0 <= selection_index < len(files):
                return os.path.join(os.getcwd(), files[selection_index])
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            # Input is not a number, assume it's a path
            if os.path.exists(user_input):
                 # Check if it's just a filename in the current dir
                 if not os.path.dirname(user_input) and os.path.exists(os.path.join(os.getcwd(), user_input)):
                     return os.path.join(os.getcwd(), user_input)
                 # Assume it's a full or relative path that exists
                 return user_input
            # If it doesn't exist but looks like a filename (no directory part), assume current dir
            elif not os.path.dirname(user_input) and extension in user_input:
                 print(f"Warning: File '{user_input}' not found, but assuming it's intended for the current directory.")
                 return os.path.join(os.getcwd(), user_input)
            # If it looks like a path but doesn't exist
            elif os.path.dirname(user_input):
                 print(f"Error: Path '{user_input}' not found. Please enter a valid path or select a number.")
            # Otherwise, treat as a filename for the current directory (especially for output)
            else:
                 print(f"Assuming '{user_input}' is a filename for the current directory.")
                 return os.path.join(os.getcwd(), user_input)
        except IndexError: # Handle potential index errors if list is empty but user enters number
             print("Invalid input. Please enter a valid path or number.")


def get_output_file_input(prompt, default_extension=".ttl"):
    """Gets the output file path, defaulting to the current directory."""
    print(f"\n{prompt}")
    user_input = input("Enter the desired output filename (e.g., 'output.ttl') or a full path: ")
    # If it's just a filename, prepend the current directory
    if not os.path.dirname(user_input):
        # Ensure it has the correct extension if none provided
        if not user_input.endswith(default_extension):
            user_input += default_extension
        return os.path.join(os.getcwd(), user_input)
    # If it's a path, use it as is
    else:
        # Ensure it has the correct extension if none provided in the filename part
        if not os.path.basename(user_input).endswith(default_extension):
             # Be careful not to add extension if it's a directory path
             if '.' not in os.path.basename(user_input):
                 print(f"Warning: Output path '{user_input}' looks like a directory. Saving as '{os.path.join(user_input, 'output' + default_extension)}'")
                 # Or handle as an error depending on desired behavior
                 # For simplicity here, we'll assume it's a filename mistake
                 return user_input + default_extension # Append extension anyway, might be wrong
             elif not user_input.endswith(default_extension):
                 # Has a different extension
                 print(f"Warning: Output file '{user_input}' does not have the expected '{default_extension}' extension.")
                 return user_input

        return user_input


def main():
    # Get inputs interactively, allowing file selection
    existing_ontology_file = get_file_input("Enter the path to the existing base ontology file (.ttl):", ".ttl")
    catalog_file = get_file_input("Enter the path to the schema catalog file (.json):", ".json")
    output_ontology_file = get_output_file_input("Enter the path for the output ontology file (.ttl):")
    platform_name = input("\nEnter the name of the platform (e.g., 'Razorpay'): ")

    print("\n--- Configuration ---")
    print(f"Base Ontology: {existing_ontology_file}")
    print(f"Catalog File:  {catalog_file}")
    print(f"Output File:   {output_ontology_file}")
    print(f"Platform Name: {platform_name}")
    print("---------------------\n")


    # Validate required input files exist before proceeding
    if not os.path.isfile(existing_ontology_file):
        print(f"Error: Base ontology file not found at '{existing_ontology_file}'")
        return
    if not os.path.isfile(catalog_file):
        print(f"Error: Catalog file not found at '{catalog_file}'")
        return

    try:
        working_ontology = Ontology(existing_ontology_file, catalog_file, output_ontology_file, platform_name)

        # Load the schema (already done in __init__, but we need schema_data here)
        with open(catalog_file, "r") as f:
            schema_data = json.load(f)

        platform_name_formatted = working_ontology.string_naming(platform_name)
        class_uri, property_uri = working_ontology.ontology_initialization(platform_name_formatted)

        # === Process Root Schema ===
        streams = schema_data.get('streams', [])
        if not streams:
             print("Warning: No 'streams' found in the catalog file.")
             # Decide if you want to exit or continue with an empty ontology
             # return # Optional: exit if no streams

        for single_schema in streams:
            root_class_name = single_schema.get("stream")
            if not root_class_name:
                print("Warning: Skipping stream with missing 'stream' key.")
                continue # Skip this stream if it doesn't have a name

            print(f"Processing stream: {root_class_name}...")
            root_class_name_formatted = working_ontology.string_naming(root_class_name)
            working_ontology.process_schema(root_class_name_formatted, single_schema, class_uri, property_uri)

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
