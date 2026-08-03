import json
import requests

# The open-source daily snapshot containing all publicly listed YC companies
DATASET_URL = "https://github.io"

# Targets mapping exact regions defined in the YC directory schema
TARGET_REGIONS = ["Europe", "South Asia", "Southeast Asia", "East Asia"]

print("Downloading the latest YC company directory snapshot...")
try:
    response = requests.get(DATASET_URL, timeout=15)
    
    if response.status_code == 200:
        all_companies = response.json()
        print(f"Total companies downloaded: {len(all_companies)}")
        
        # Filter the universal list down to your desired regions locally
        filtered_startups = [
            company for company in all_companies 
            if company.get("region") in TARGET_REGIONS
        ]
        
        print(f"Filtered down to {len(filtered_startups)} European and Asian companies.")
        
        # Save the structured data locally
        output_filename = "yc_europe_asia_startups.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(filtered_startups, f, indent=4)
            
        print(f"Successfully saved data to '{output_filename}'.")
        
    else:
        print(f"Failed to pull snapshot. Server returned status: {response.status_code}")

except Exception as e:
    print(f"An error occurred while downloading the dataset: {e}")




# import requests

# # YC's public Algolia search endpoint
# url = "https://algolia.net"

# # Payload filtering exclusively for African startups
# payload = {
#     "query": "",
#     "facetFilters": [["regions:Europe"]],
#     "hitsPerPage": 1000 
# }

# response = requests.post(url, json=payload)
# startups = response.json().get("hits", [])

# # Print structural information from the first African startup found
# if startups:
#     print(startups[0].keys())
