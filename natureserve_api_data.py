#!/usr/bin/env python3
"""
Script to collect endangered bee species data from NatureServe Explorer API.
Requires: requests library (pip install requests)

NatureServe Conservation Statuses:
https://explorer.natureserve.org/AboutTheData/DataTypes/ConservationStatusCategories

NatureServe API docs:

https://explorer.natureserve.org/api-docs/
"""

import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
import ipdb
from collections import defaultdict

PER_PAGE_FAMILY_SEARCH = 100

class NatureServeBeeData:
	
	
	def __init__(self):
		self.base_url = "https://explorer.natureserve.org/api"
		
		# NatureServe conservation status codes we care about
		# G = Global, N = National, S = Subnational (state/province)
		self.target_granks = ['GX', 'GH', 'G1', 'G2', 'G3']  # Extinct to Vulnerable globally
		self.target_nranks = ['NX', 'NH', 'N1', 'N2', 'N3']  # National level
		
		# Map NatureServe ranks to IUCN-like categories
		self.rank_map = {
			'GX': 'EX',  # Presumed Extinct
			'GH': 'EW',  # Possibly Extinct
			'G1': 'CR',  # Critically Imperiled
			'G2': 'EN',  # Imperiled
			'G3': 'VU',  # Vulnerable
			'NX': 'EX',
			'NH': 'EW',
			'N1': 'CR',
			'N2': 'EN',
			'N3': 'VU'
		}
		
		# Bee families
		self.bee_families = [
			'Apidae',
			'Megachilidae',
			'Halictidae',
			'Andrenidae',
			'Colletidae',
			'Melittidae',
			'Stenotritidae'
		]
		
		self.results = []
	
	def get_taxon_by_uid(self, element_uid: str) -> Optional[Dict]:
		"""
		Get detailed information for a specific taxon using its Element Global UID.
		"""
		endpoint = f"{self.base_url}/data/taxon/{element_uid}"
		
		try:
			#ipdb.set_trace()
			response = requests.get(endpoint, timeout=30)
			#ipdb.set_trace()
			if response.status_code == 200:
				return response.json()
			else:
				print(f"    Error getting {element_uid}: HTTP {response.status_code}")
		except requests.exceptions.RequestException as e:
			print(f"    Request error for {element_uid}: {e}")
		
		return None
	
	def extract_conservation_info(self, taxon_data: Dict) -> Optional[Dict]:
		"""
		Extract relevant conservation information from taxon data.
		"""
		if not taxon_data:
			return None
		
		scientific_name = taxon_data.get('scientificName', '')
		common_name = taxon_data.get('primaryCommonName', '')
		
		# Get global rank (rounded)
		rounded_grank = taxon_data.get('roundedGRank', '')
		grank = taxon_data.get('grank', '')
		
		# Check if it matches our target conservation statuses
		is_threatened = False
		conservation_status = None
		
		# Check global rank
		if rounded_grank in self.target_granks:
			is_threatened = True
			conservation_status = self.rank_map.get(rounded_grank, rounded_grank)
		
		# Also check national ranks
		national_ranks = []
		element_nationals = taxon_data.get('elementNationals', [])
		for national in element_nationals:
			nation_name = national.get('nation', {}).get('nameEn', '')
			rounded_nrank = national.get('roundedNRank', '')
			nrank = national.get('nrank', '')
			
			if rounded_nrank in self.target_nranks:
				is_threatened = True
				national_ranks.append({
					'nation': nation_name,
					'rank': rounded_nrank,
					'full_rank': nrank,
					'status': self.rank_map.get(rounded_nrank, rounded_nrank)
				})
		
		if not is_threatened:
			return None
		
		# Get taxonomy info
		name_category = taxon_data.get('nameCategory', {})
		taxonomic_category = name_category.get('nameCategoryDescEn', '')
		
		return {
			'scientific_name': scientific_name,
			'common_name': common_name,
			'element_uid': taxon_data.get('uniqueId', ''),
			#'taxonomic_category': taxonomic_category,
			'global_rank': rounded_grank,
			'global_rank_full': grank,
			'conservation_status': conservation_status,
			#'national_ranks': national_ranks,
			'iucn': taxon_data.get('iucn', {}),
			#'taxonomic_comments': taxon_data.get('taxonomicComments', ''),
			'last_modified': taxon_data.get('lastModified', ''),
			'ns_url': f"https://explorer.natureserve.org{taxon_data.get('nsxUrl', '')}"
		}
	
	def search_bees_by_family(self, family_name: str) -> List[Dict]:
		"""
		Search for all bee species in a given family using taxonomy criteria.
		"""
		print(f"\nSearching NatureServe for {family_name}...")
		
		endpoint = f"{self.base_url}/data/speciesSearch"
		
		# Search using speciesTaxonomyCriteria to filter by family
		# Format based on working StackOverflow example - all arrays must be lists
		search_body = {
			'criteriaType': 'species',
			'textCriteria': [],
			'statusCriteria': [
        {
          "paramType" : "globalRank",
          "globalRank" : "G1"
        },
				{
          "paramType" : "globalRank",
          "globalRank" : "G2"
        },
				{
          "paramType" : "globalRank",
          "globalRank" : "G3"
        },
				{
          "paramType" : "globalRank",
          "globalRank" : "GX"
        },
				{
          "paramType" : "globalRank",
          "globalRank" : "GH"
        },
      ],
			'locationCriteria': [],
			'pagingOptions': {
        "page" : 0,
        "recordsPerPage" : PER_PAGE_FAMILY_SEARCH
      },
			'recordSubtypeCriteria': None,
			'modifiedSince': None,
			'locationOptions': None,
			'classificationOptions': None,
			'speciesTaxonomyCriteria': [{
				'paramType': 'scientificTaxonomy',
				'level': 'family',
				'scientificTaxonomy': family_name,
				'kingdom': "Animalia"
			}]
		}
		
		threatened_species = []
		
		try:
			response = requests.post(endpoint, json=search_body, timeout=30)
			#ipdb.set_trace()
			if response.status_code == 200:
				data = response.json()
				results = data.get('results', [])
				
				print(f"  Found {len(results)} total species in {family_name}")
				
				for result in results:
					# Check conservation status from search results
					rounded_grank = result.get('roundedGRank', '')
					
					# Only process if it has a threatened status
					if rounded_grank in self.target_granks:
						scientific_name = result.get('scientificName', '')
						print(f"    → Threatened: {scientific_name} ({rounded_grank})")
						
						# Get full details
						element_uid = result.get('uniqueId', '')
						if element_uid:
							full_data = self.get_taxon_by_uid(element_uid)
							
							if full_data:
								conservation_info = self.extract_conservation_info(full_data)
								if conservation_info:
									conservation_info['family'] = family_name
									threatened_species.append(conservation_info)
							
							time.sleep(0.5)  # Rate limiting
			else:
				print(f"  Error: HTTP {response.status_code}")
				if response.status_code == 400:
					print(f"  Response: {response.text[:500]}")
					
		except requests.exceptions.RequestException as e:
			print(f"  Request error: {e}")
		
		return threatened_species
	
	def collect_all_bee_data(self):
		"""
		Main function to collect conservation data for all bee families.
		"""
		print("=" * 70)
		print("NATURESERVE BEE CONSERVATION DATA COLLECTION")
		print("=" * 70)
		
		for family in self.bee_families:
			family_species = self.search_bees_by_family(family)
			self.results.extend(family_species)
			time.sleep(1)  # Be respectful with rate limiting
		
		print(f"\n\n{'='*70}")
		print(f"Total threatened bee species found: {len(self.results)}")
		print(f"{'='*70}")
		
		return self.results
	
	def save_results(self, filename: str = 'natureserve_bees.json'):
		"""Save results to a JSON file."""
		output = {
			'collection_date': datetime.now().isoformat(),
			'total_species': len(self.results),
			'data_source': 'NatureServe Explorer',
			'species': self.results
		}
		
		with open(filename, 'w', encoding='utf-8') as f:
			json.dump(output, f, indent=2, ensure_ascii=False)
		
		print(f"\n✓ Results saved to {filename}")
	
	def print_summary(self):
		"""Print a summary of collected data."""
		print("\n" + "=" * 70)
		print("SUMMARY")
		print("=" * 70)
		
		# Count by family
		family_counts = defaultdict(int)
		for species in self.results:
			family = species.get('family', 'Unknown')
			family_counts[family] += 1
		
		print(f"\nTotal species found: {len(self.results)}")
		print("\nBy family:")
		for family, count in sorted(family_counts.items()):
			print(f"  {family}: {count}")
		
		# Count by conservation status
		status_counts = defaultdict(int)
		for species in self.results:
			status = species.get('conservation_status', 'Unknown')
			status_counts[status] += 1
		
		print("\nBy conservation status:")
		for status in ['EX', 'EW', 'CR', 'EN', 'VU']:
			count = status_counts.get(status, 0)
			if count > 0:
				print(f"  {status}: {count}")
		
		# Show some examples
		if self.results:
			print(f"\nExample species (showing first 5 of {len(self.results)}):")
			for i, species in enumerate(self.results[:5], 1):
				print(f"\n  {i}. {species['scientific_name']}")
				if species.get('common_name'):
					print(f"     Common name: {species['common_name']}")
				print(f"     Family: {species['family']}")
				print(f"     Global rank: {species['global_rank_full']} ({species['conservation_status']})")
				if species.get('national_ranks'):
					for nat_rank in species['national_ranks'][:2]:  # Show first 2
						print(f"     {nat_rank['nation']}: {nat_rank['full_rank']} ({nat_rank['status']})")
				print(f"     URL: {species['ns_url']}")

def main():
	"""Main execution function."""
	collector = NatureServeBeeData()
	
	print("NatureServe Explorer API - Bee Conservation Status")
	print("This script searches for threatened bee species across all major bee families.")
	print("\nNatureServe Ranks:")
	print("  GX/NX = Presumed Extinct")
	print("  GH/NH = Possibly Extinct")
	print("  G1/N1 = Critically Imperiled")
	print("  G2/N2 = Imperiled")
	print("  G3/N3 = Vulnerable")
	print()
	
	# Collect all data
	collector.collect_all_bee_data()
	
	# Print summary
	collector.print_summary()
	
	# Save results
	collector.save_results()
	
	print("\n" + "=" * 70)
	print("DATA COLLECTION COMPLETE")
	print("=" * 70)
	print("\nNext steps:")
	print("1. Review natureserve_bees.json for detailed species information")
	print("2. Cross-reference with iNaturalist data for observation records")
	print("3. Check NatureServe URLs for full conservation assessments")

if __name__ == "__main__":
	main()