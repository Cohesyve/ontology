import rdflib
import pandas as pd

def ttl_to_excel(ttl_file, output_excel, segregate_by_platform=True):
    # Load the RDF graph
    g = rdflib.Graph()
    g.parse(ttl_file, format="turtle")
    
    # Namespaces for querying
    OWL = rdflib.Namespace("http://www.w3.org/2002/07/owl#")
    RDFS = rdflib.Namespace("http://www.w3.org/2000/01/rdf-schema#")
    
    # Extract classes
    classes_query = """
    SELECT DISTINCT 
        ?parentClass
        ?parentClassLabel
        ?subClass
        ?subClassLabel
        ?subClassDefinition
    WHERE {
        ?subClass a owl:Class .
        ?subClass rdfs:label ?subClassLabel .
        ?subClass rdfs:isDefinedBy ?subClassDefinition .
        ?subClass rdfs:subClassOf ?parentClass .
        ?parentClass rdfs:label ?parentClassLabel .
        FILTER(CONTAINS(STR(?parentClassLabel), "PlatformField"))
    }
    """
    results = g.query(classes_query)
    classes = [row for row in g.query(classes_query)]

    # print(classes)
    
    # Prepare data for Excel
    data = []
    
    data = {}
    for cls in classes:
        # Unpack the class details from the query results
        parent_class_uri = cls[0]
        parent_class_label = str(cls[1])
        subclass_uri = cls[2]
        subclass_label = str(cls[3])
        subclass_definition = str(cls[4])
        
        # Query properties for the current parent class and subclass
        properties_query = f"""
        SELECT DISTINCT 
            ?parentPropertyLabel
            ?propertyLabel
            ?subpropertyLabel
            ?subClassDefinition
            ?subpropertyType
            (BOUND(?isPrimaryKeyValue) AS ?isPrimaryKey)
        WHERE {{
            ?parentProperty a owl:DatatypeProperty .
            ?parentProperty rdfs:label ?parentPropertyLabel .
            ?parentProperty rdfs:domain <{parent_class_uri}> .
            ?property rdfs:subPropertyOf+ ?parentProperty .
            ?property rdfs:domain <{subclass_uri}> .
            ?property rdfs:label ?propertyLabel .
            ?subproperty rdfs:subPropertyOf+ ?property .
            ?subproperty rdfs:label ?subpropertyLabel .
            ?subproperty rdfs:isDefinedBy ?subClassDefinition .
            ?subproperty rdfs:range ?subpropertyType .
            OPTIONAL {{
            ?subproperty <https://www.cohesyve.com/ontologies/D2C#isPrimaryKey> ?isPrimaryKeyValue .
            }}
        }}
        """
        properties = [row for row in g.query(properties_query)]
        
        # Organize data: group by parent class then by subclass
        if parent_class_label not in data:
            data[parent_class_label] = {}
        if subclass_label not in data[parent_class_label]:
            data[parent_class_label][subclass_label] = {
                "definition": subclass_definition,
                "properties": []
            }
        # Append property details to the subclass:
        for row in properties:
            property_details = {
                "name": str(row[2]),
                "definition": str(row[3]),
                "type": str(row[4]).replace('http://www.w3.org/2001/XMLSchema#', ''),
                "isPrimaryKey": bool(row[5])
            }
            data[parent_class_label][subclass_label]["properties"].append(property_details)

    # print(data)
    
    # Convert to DataFrame

    if segregate_by_platform:
        with pd.ExcelWriter(output_excel) as writer:
            for parent, subclasses in data.items():
                rows = []
                for subclass, details in subclasses.items():
                    for prop in details["properties"]:
                        rows.append({
                            "Entity": subclass,
                            "Property Name": prop["name"],
                            "Property Definition": prop["definition"],
                            "Property Type": prop["type"],
                            "Is Primary Key": prop["isPrimaryKey"],
                        })
                df = pd.DataFrame(rows)
                # Excel sheet names allow a maximum of 31 characters; trim if needed and remove invalid characters.
                sheet_name = parent[:31].replace('/', '_').replace('\\', '_')
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Data saved to {output_excel} with separate sheets for each platform.")
    else:
        rows = []
        for parent, subclasses in data.items():
            for subclass, details in subclasses.items():
                for prop in details["properties"]:
                    rows.append({
                        "Platform": parent,
                        "Entity": subclass,
                        "Property Name": prop["name"],
                        "Property Definition": prop["definition"],
                        "Property Type": prop["type"],
                        "Is Primary Key": prop["isPrimaryKey"],
                    })
        df = pd.DataFrame(rows)

        # Save to Excel
        df.to_excel(output_excel, index=False)
        print(f"Data saved to {output_excel}")

# Example usage
ttl_to_excel("D2C Ontology.ttl", "cohesyve-platform-data-points.xlsx")