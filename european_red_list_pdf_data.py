#!/usr/bin/env python3
"""
Parse European Red List Appendix 1 table to extract threatened and near-threatened bees.
Extracts only: CR, EN, VU, NT (excludes LC and DD species)
"""

import json
from datetime import datetime
from tabula.io import read_pdf
import ipdb
from collections import defaultdict

TARGET_STATUSES = {'CR', 'EN', 'VU', 'NT'}
ALL_STATUSES = {'CR', 'EN', 'VU', 'NT', 'DD', 'LC'}

def main():
  """Main execution - parse the table and create JSON."""
  
  print("=" * 70)
  print("EUROPEAN RED LIST APPENDIX 1 PARSER")
  print("=" * 70)
  print("\nExtracting threatened and near-threatened species (CR, EN, VU, NT)")
  print("Excluding: LC (Least Concern) and DD (Data Deficient)")
  print()
  

if __name__ == "__main__":
  
  # Read tables from a PDF file
  # 'data.pdf' is the path to your PDF file
  # pages='all' extracts tables from all pages; specify page numbers if needed (e.g., pages='1-3')
  species_list = []
  dfs = read_pdf("red list euro bees.pdf", pages='all', multiple_tables=True, guess=False, stream=True)
  # dfs will be a list of pandas DataFrames, where each DataFrame represents a table found in the PDF.
  # You can then iterate through the list and process each DataFrame.
  family_count, family_dd_count = 0, 0
  family_name = None
  genus, species, iucn_europe, iucn_eu_27, endemic_europe, endemic_eu27 = None, None, None, None, None, None
  done = False
  family_counts = defaultdict(dict)
  for this_row, df in enumerate(dfs):
   # print(f"Table {row+1}:\n")
    for index, row in df.iterrows(): # type: ignore
      if index < 5:
        continue
      
      try:
        data = [str(r) for r in row]
        if data[0].isdigit(): # bogus parsing for end of current page (first digit is prob page number or something)
          continue
      except ValueError: # is NaN
        continue

      data = (" ".join(data)).split()

      if "Dasypoda" in data and not done:
        family_name = "MELITTIDAE"
        family_counts[family_name] = defaultdict(int) 
        family_count = 0
        family_dd_count = 0
        done = True
      if len(data) == 1 or data[0].isupper():
        family_name = data[0]
        family_count = 0
        family_dd_count = 0
        family_counts[family_name] = defaultdict(int)
        continue
      elif len(data) == 6:
        genus, species, iucn_europe, iucn_eu_27, endemic_europe, endemic_eu27 = data
      elif len(data) == 7:
        genus, species, iucn_europe, var_1, var_2, endemic_europe, endemic_eu27 = data # we deliberate miss iucn_eu_27 data here
        iucn_eu_27 = var_2 if var_1 == 'nan' else var_1
      elif len(data) == 8:
        genus, species, iucn_europe, _, iucn_eu_27, _, endemic_europe, endemic_eu27 = data

      if iucn_europe in TARGET_STATUSES:
        family_counts[family_name]['Threatened'] += 1
      else:
        if iucn_europe in {'LC', 'DD'}:
          family_counts[family_name][iucn_europe] += 1

      species_list.append({
        'scientific_name': f"{genus} {species}",
        'family': family_name,
        'iucn_europe_status': iucn_europe,
        'iucn_eu_27_status': iucn_eu_27,
        'endemic_to_europe': endemic_europe == "Yes",
        'endemic_to_eu27': endemic_eu27 == "Yes"
      })
      
      
    #print("\n" + "="*30 + "\n")

  if species_list:
    # Create output
    output = {
      'data_source': 'European Red List of Bees - Appendix 1',
      'reference': 'Nieto et al. 2014',
      'pdf_url': 'https://portals.iucn.org/library/sites/library/files/documents/RL-4-019.pdf',
      'collection_date': datetime.now().isoformat(),
      'geographic_scope': 'Europe',
      'note': 'Includes only threatened (CR, EN, VU) and near-threatened (NT) species',
      'total_species': len(species_list),
      'species': species_list
    }
    
    with open('european_redlist_conservation_concern.json', 'w', encoding='utf-8') as f:
      json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Count by status
    status_counts = defaultdict(int)
    for sp in species_list:
      status = sp['iucn_europe_status']
      status_counts[status] += 1

    print("\nBreakdown by conservation status:")
    for status in ALL_STATUSES:
      count = status_counts.get(status, 0)
      if count > 0:
        print(f"  {status}: {count}")
    
    threatened_species = [s for s in species_list if s['iucn_europe_status'] in TARGET_STATUSES and s['iucn_eu_27_status'] in TARGET_STATUSES]
    
    print("\nBreakdown by family (Europe-wide status, ignoring EU-specific data here)")
    total_dd_count = 0
    total_count_all_families = 0
    for family, counts in sorted(family_counts.items()):
      dd_count = 0
      total_count = sum(counts.values())
      print(f"  {family}")
      for key, value in counts.items():
        total_count_all_families += value
        if key == 'DD':
          dd_count += value

      print(f"    % Data-Deficient: {round((dd_count / total_count) * 100, 1)}")
      print(f"    % Threatened:     {round((counts['Threatened'] / total_count) * 100, 1)}")
      print(f"    % Least Concern:  {round((counts['LC'] / total_count) * 100, 1)}")
      total_dd_count += dd_count
    print(f"\n DD % across all species: {(total_dd_count / total_count_all_families) * 100}")
    endemic_europe_count = sum(1 for sp in species_list if sp['endemic_to_europe'])
    endemic_eu_count = sum(1 for sp in species_list if sp['endemic_to_eu27'])

    print("\nBreakdown by Species Nativity")
    print(f"  Endemic to Europe: {endemic_europe_count} species")
    print(f"  Endemic to EU 27: {endemic_eu_count} species")

    print(f"\nExtracted {len(threatened_species)} conservation-relevant species")
  else:
    print("Failed to parse. Running main() for instructions...")
    main()