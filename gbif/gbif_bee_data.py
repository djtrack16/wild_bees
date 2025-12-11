#!/usr/bin/env python3
"""
Script to collect bee occurrence data from GBIF API.
Requires: requests library (pip install requests)
"""

import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime

class GBIFBeeData:
	def __init__(self):
		self.base_url = "https://api.gbif.org/v1"
		
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
		
		# IUCN Red List categories we care about
		self.target_iucn_categories = ['EX', 'EW', 'CR', 'EN', 'VU', 'NT']
		self.iucn_categories = ['EXTINCT', 'EXTINCT_IN_THE_WILD', 'REGIONALLY_EXTINCT', 'CRITICALLY_ENDANGERED', 'ENDANGERED', 'VULNERABLE', 'NEAR_THREATENED']
		
		# Cache for family taxon keys
		self.family_keys = {}
		
		self.results = []
	
	def get_species_info(self, species_key: int) -> Optional[Dict]:
		"""
		Get basic species information from a species key.
		"""
		endpoint = f"{self.base_url}/species/{species_key}"
		
		try:
			response = requests.get(endpoint, timeout=30)
			if response.status_code == 200:
				return response.json()
		except requests.exceptions.RequestException:
			pass
		
		return None
	
	def get_family_taxon_key(self, family_name: str) -> Optional[int]:
		"""
		Get the GBIF taxonKey for a bee family.
		"""
		if family_name in self.family_keys:
			return self.family_keys[family_name]
		
		endpoint = f"{self.base_url}/species/match"
		params = {
			'name': family_name,
			'rank': 'FAMILY',
			'kingdom': 'Animalia'
		}
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				if data.get('matchType') in ['EXACT', 'FUZZY']:
					taxon_key = data.get('usageKey')
					self.family_keys[family_name] = taxon_key
					return taxon_key
				else:
					print(f"  Warning: Could not find exact match for {family_name}")
			else:
				print(f"  Error getting taxon key for {family_name}: HTTP {response.status_code}")
		except requests.exceptions.RequestException as e:
			print(f"  Request error for {family_name}: {e}")
		
		return None
	
	def search_occurrences_by_species(self, scientific_name: str, iucn_category: str = None) -> Dict:
		"""
		Search for occurrences of a specific species.
		Returns summary statistics and recent occurrences.
		"""
		endpoint = f"{self.base_url}/occurrence/search"
		
		# Build search parameters
		params = {
			'scientificName': scientific_name,
			'hasCoordinate': 'true',  # Only records with coordinates
			'limit': 20,  # Get 20 most recent
			'offset': 0
		}
		
		if iucn_category:
			params['iucnRedListCategory'] = iucn_category
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				
				total_count = data.get('count', 0)
				results = data.get('results', [])
				
				# Extract 5 most recent occurrences that are not human observations.
				# Most human observations come from iNaturalist database, whose API is being queried separately
				occurrences = []
				for occ in [r for r in results if r.get('basisOfRecord') != 'HUMAN_OBSERVATION'][:5]:  # Just keep 5 most recent
					occurrences.append({
						'gbif_id': occ.get('key'),
						'date': occ.get('eventDate'),
						'year': occ.get('year'),
						'country': occ.get('country'),
						'state_province': occ.get('stateProvince'),
						'locality': occ.get('locality'),
						'latitude': occ.get('decimalLatitude'),
						'longitude': occ.get('decimalLongitude'),
						'basis_of_record': occ.get('basisOfRecord'),
						'dataset_key': occ.get('datasetKey'),
						'institution_code': occ.get('institutionCode')
					})
				
				return {
					'total_occurrences': total_count,
					'recent_occurrences': occurrences
				}
			else:
				print(f"    Error searching occurrences: HTTP {response.status_code}")
		except requests.exceptions.RequestException as e:
			print(f"    Request error: {e}")
		
		return {'total_occurrences': 0, 'recent_occurrences': []}
	
	def get_threatened_species_in_family(self, family_key: int, family_name: str) -> List[Dict]:
		"""
		Get all threatened species within a family using occurrence search with facets.
		This is more efficient than searching species lists.
		"""
		print(f"\nSearching GBIF occurrences for threatened species in {family_name}...")
		
		endpoint = f"{self.base_url}/occurrence/search"
		
		threatened_species = []
		
		# Search for each IUCN category separately to get species lists
		for iucn_cat in self.target_iucn_categories:
			params = {
				'familyKey': family_key,
				'iucnRedListCategory': iucn_cat,
				'facet': 'speciesKey',
				'facetLimit': 10000,  # Max species per category
				'limit': 0  # We don't need actual occurrence records, just facet counts
			}
			
			try:
				response = requests.get(endpoint, params=params, timeout=30)
				if response.status_code == 200:
					data = response.json()
					
					# Get species from facets
					facets = data.get('facets', [])
					for facet in facets:
						if facet.get('field') == 'SPECIES_KEY':
							counts = facet.get('counts', [])
							print(f"  {iucn_cat}: Found {len(counts)} species")
							
							for count_obj in counts:
								species_key = count_obj.get('name')
								occurrence_count = count_obj.get('count', 0)
								
								# Get species name from the key
								species_info = self.get_species_info(species_key)
								if species_info:
									threatened_species.append({
										'scientific_name': species_info.get('scientificName'),
										'species_key': species_key,
										'iucn_category': iucn_cat,
										'family': family_name,
										'total_occurrences': occurrence_count
									})
				else:
					print(f"  Error for {iucn_cat}: HTTP {response.status_code}")
				
				time.sleep(0.3)  # Rate limiting
				
			except requests.exceptions.RequestException as e:
				print(f"  Request error for {iucn_cat}: {e}")
		
		print(f"  Total threatened species found: {len(threatened_species)}")
		return threatened_species
	
	def collect_all_bee_data(self):
		"""
		Main function to collect bee occurrence data from GBIF.
		"""
		print("=" * 70)
		print("GBIF BEE OCCURRENCE DATA COLLECTION")
		print("=" * 70)
		print("\nStep 1: Getting family taxon keys...")
		
		# First, get all family keys
		for family in self.bee_families:
			key = self.get_family_taxon_key(family)
			if key:
				print(f"  {family}: {key}")
		
		print("\nStep 2: Finding threatened species in each family...")
		
		# Get all threatened species using occurrence facets
		all_threatened_species = []
		for family in self.bee_families:
			family_key = self.family_keys.get(family)
			if family_key:
				species_list = self.get_threatened_species_in_family(family_key, family)
				all_threatened_species.extend(species_list)
				time.sleep(1)
		
		print(f"\nStep 3: Getting occurrence data for {len(all_threatened_species)} threatened species...")
		
		# Get occurrence data for each species
		for i, species_info in enumerate(all_threatened_species, 1):
			scientific_name = species_info['scientific_name']
			iucn_cat = species_info['iucn_category']
			
			print(f"  [{i}/{len(all_threatened_species)}] {scientific_name} ({iucn_cat})...")
			
			occurrence_data = self.search_occurrences_by_species(
				scientific_name,
				iucn_cat
			)
			
			# Combine species info with occurrence data
			result = {
				**species_info,
				**occurrence_data
			}
			
			self.results.append(result)
			
			time.sleep(0.3)  # Rate limiting
		
		print(f"\n{'='*70}")
		print(f"Total species processed: {len(self.results)}")
		print(f"{'='*70}")
		
		return self.results
	
	def save_results(self, filename: str = 'gbif_bees.json'):
		"""Save results to a JSON file."""
		output = {
			'collection_date': datetime.now().isoformat(),
			'total_species': len(self.results),
			'data_source': 'GBIF',
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
		family_counts = {}
		for species in self.results:
			family = species.get('family', 'Unknown')
			family_counts[family] = family_counts.get(family, 0) + 1
		
		print(f"\nTotal species found: {len(self.results)}")
		print("\nBy family:")
		for family, count in sorted(family_counts.items()):
			print(f"  {family}: {count}")
		
		# Count by IUCN category
		iucn_counts = {}
		for species in self.results:
			cat = species.get('iucn_category', 'Unknown')
			iucn_counts[cat] = iucn_counts.get(cat, 0) + 1
		
		print("\nBy IUCN Red List Category:")
		for cat in ['EX', 'EW', 'CR', 'EN', 'VU', 'NT']:
			count = iucn_counts.get(cat, 0)
			if count > 0:
				print(f"  {cat}: {count}")
		
		# Count species with occurrence records
		species_with_occurrences = [s for s in self.results if s.get('total_occurrences', 0) > 0]
		print(f"\nSpecies with occurrence records: {len(species_with_occurrences)}")
		
		# Show total occurrences
		total_occurrences = sum(s.get('total_occurrences', 0) for s in self.results)
		print(f"Total occurrence records: {total_occurrences:,}")
		
		# Show some examples
		if species_with_occurrences:
			print(f"\nExample species with most occurrences (top 5):")
			sorted_species = sorted(self.results, key=lambda x: x.get('total_occurrences', 0), reverse=True)
			for i, species in enumerate(sorted_species[:5], 1):
				print(f"\n  {i}. {species['scientific_name']}")
				print(f"     Family: {species['family']}")
				print(f"     IUCN: {species['iucn_category']}")
				print(f"     Occurrences: {species['total_occurrences']:,}")
				if species.get('recent_occurrences'):
					latest = species['recent_occurrences'][0]
					print(f"     Latest record: {latest['date']} in {latest['country']}")

def main():
	"""Main execution function."""
	collector = GBIFBeeData()
	
	print("GBIF API - Bee Occurrence Data Collection")
	print("This script searches for occurrence records of threatened bee species.")
	print("\nIUCN Red List Categories included:")
	print("  EX  = Extinct")
	print("  EW  = Extinct in the Wild")
	print("  CR  = Critically Endangered")
	print("  EN  = Endangered")
	print("  VU  = Vulnerable")
	print("  NT  = Near Threatened")
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
	print("1. Review gbif_bees.json for occurrence data")
	print("2. Cross-reference with NatureServe and iNaturalist data")
	print("3. Use occurrence coordinates for mapping distributions")

if __name__ == "__main__":
	main()