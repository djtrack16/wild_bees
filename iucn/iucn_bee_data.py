#!/usr/bin/env python3
"""
Script to collect bee conservation data from IUCN Red List API.
Requires: requests library (pip install requests)

Get your free API token at: https://api.iucnredlist.org/users/sign_up
"""

import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime

class IUCNBeeData:
	def __init__(self, api_token: str):
		self.base_url = "https://api.iucnredlist.org/api/v4"
		
		# Get token from parameter or environment variable
		self.api_token = api_token or "YOUR_IUCN_API_TOKEN_HERE"
		
		# Bee families
		self.bee_families = [
			'APIDAE',
			'MEGACHILIDAE',
			'HALICTIDAE',
			'ANDRENIDAE',
			'COLLETIDAE',
			'MELITTIDAE',
			'STENOTRITIDAE'
		]
		
		# IUCN Red List categories we care about
		self.target_categories = ['EX', 'EW', 'CR', 'EN', 'VU', 'NT']
		
		self.results = []
	
	def get_species_by_taxon(self, taxon_name: str) -> List[Dict]:
		"""
		Get all species assessments for a given taxon (e.g., family).
		"""
		endpoint = f"{self.base_url}/taxa/search"
		params = {
			'token': self.api_token,
			'taxa': taxon_name
		}
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				return data.get('results', [])
			else:
				print(f"  Error: HTTP {response.status_code}")
				if response.status_code == 401:
					print("  Authentication failed. Check your API token.")
				elif response.status_code == 404:
					print(f"  Taxon '{taxon_name}' not found.")
		except requests.exceptions.RequestException as e:
			print(f"  Request error: {e}")
		
		return []
	
	def get_species_assessment(self, scientific_name: str) -> Optional[Dict]:
		"""
		Get detailed assessment for a specific species by scientific name.
		"""
		# URL encode the species name
		encoded_name = scientific_name.replace(' ', '%20')
		endpoint = f"{self.base_url}/species/{encoded_name}"
		params = {'token': self.api_token}
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				return data.get('result', {})
			elif response.status_code == 404:
				# Species not found - might not have IUCN assessment
				return None
		except requests.exceptions.RequestException as e:
			print(f"    Error getting assessment: {e}")
		
		return None
	
	def get_species_threats(self, scientific_name: str) -> List[Dict]:
		"""
		Get threat information for a species.
		"""
		encoded_name = scientific_name.replace(' ', '%20')
		endpoint = f"{self.base_url}/species/{encoded_name}/threats"
		params = {'token': self.api_token}
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				return data.get('result', [])
		except requests.exceptions.RequestException:
			pass
		
		return []
	
	def get_species_habitats(self, scientific_name: str) -> List[Dict]:
		"""
		Get habitat information for a species.
		"""
		encoded_name = scientific_name.replace(' ', '%20')
		endpoint = f"{self.base_url}/species/{encoded_name}/habitats"
		params = {'token': self.api_token}
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				return data.get('result', [])
		except requests.exceptions.RequestException:
			pass
		
		return []
	
	def get_species_conservation_measures(self, scientific_name: str) -> List[Dict]:
		"""
		Get conservation measures for a species.
		"""
		encoded_name = scientific_name.replace(' ', '%20')
		endpoint = f"{self.base_url}/species/{encoded_name}/conservation_measures"
		params = {'token': self.api_token}
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				return data.get('result', [])
		except requests.exceptions.RequestException:
			pass
		
		return []
	
	def search_bees_in_family(self, family_name: str) -> List[Dict]:
		"""
		Search for threatened bee species in a given family.
		"""
		print(f"\nSearching IUCN for {family_name}...")
		
		# Get all species in the family
		species_list = self.get_species_by_taxon(family_name)
		
		threatened_species = []
		
		for species_info in species_list:
			scientific_name = species_info.get('scientific_name', '')
			category = species_info.get('category', '')
			
			# Only process threatened species
			if category in self.target_categories:
				print(f"  Found: {scientific_name} ({category})")
				
				# Get full assessment details
				assessment = self.get_species_assessment(scientific_name)
				
				if assessment:
					# Get additional details
					threats = self.get_species_threats(scientific_name)
					habitats = self.get_species_habitats(scientific_name)
					conservation_measures = self.get_species_conservation_measures(scientific_name)
					
					result = {
						'scientific_name': scientific_name,
						'family': family_name,
						'iucn_category': category,
						'assessment': assessment,
						'threats': threats,
						'habitats': habitats,
						'conservation_measures': conservation_measures
					}
					
					threatened_species.append(result)
				
				time.sleep(2)  # IUCN recommends 2-second delay between calls
		
		print(f"  Total threatened species: {len(threatened_species)}")
		return threatened_species
	
	def collect_all_bee_data(self):
		"""
		Main function to collect bee conservation data from IUCN.
		"""
		print("=" * 70)
		print("IUCN RED LIST BEE CONSERVATION DATA COLLECTION")
		print("=" * 70)
		print()
		
		if self.api_token == "YOUR_IUCN_API_TOKEN_HERE":
			print("⚠️  ERROR: No API token configured!")
			print("\nTo use this script:")
			print("1. Sign up at: https://api.iucnredlist.org/users/sign_up")
			print("2. Request a token (approval is usually quick)")
			print("3. Replace 'YOUR_IUCN_API_TOKEN_HERE' in the script")
			print("\nOr pass the token when creating the object:")
			print("   collector = IUCNBeeData(api_token='your_token_here')")
			return []
		
		for family in self.bee_families:
			family_species = self.search_bees_in_family(family)
			self.results.extend(family_species)
			time.sleep(2)
		
		print(f"\n{'='*70}")
		print(f"Total threatened bee species found: {len(self.results)}")
		print(f"{'='*70}")
		
		return self.results
	
	def save_results(self, filename: str = 'iucn_bees.json'):
		"""Save results to a JSON file."""
		output = {
			'collection_date': datetime.now().isoformat(),
			'total_species': len(self.results),
			'data_source': 'IUCN Red List',
			'api_version': 'v4',
			'species': self.results
		}
		
		with open(filename, 'w', encoding='utf-8') as f:
			json.dump(output, f, indent=2, ensure_ascii=False)
		
		print(f"\n✓ Results saved to {filename}")
	
	def print_summary(self):
		"""Print a summary of collected data."""
		if not self.results:
			return
		
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
		category_counts = {}
		for species in self.results:
			cat = species.get('iucn_category', 'Unknown')
			category_counts[cat] = category_counts.get(cat, 0) + 1
		
		print("\nBy IUCN Red List Category:")
		for cat in ['EX', 'EW', 'CR', 'EN', 'VU', 'NT']:
			count = category_counts.get(cat, 0)
			if count > 0:
				print(f"  {cat}: {count}")
		
		# Count species with threat data
		species_with_threats = [s for s in self.results if s.get('threats')]
		print(f"\nSpecies with documented threats: {len(species_with_threats)}")
		
		# Count species with habitat data
		species_with_habitats = [s for s in self.results if s.get('habitats')]
		print(f"Species with habitat data: {len(species_with_habitats)}")
		
		# Show examples
		if self.results:
			print(f"\nExample species (first 3):")
			for i, species in enumerate(self.results[:3], 1):
				print(f"\n  {i}. {species['scientific_name']}")
				print(f"     Family: {species['family']}")
				print(f"     IUCN: {species['iucn_category']}")
				
				assessment = species.get('assessment', {})
				if assessment:
					pop_trend = assessment.get('population_trend', 'Unknown')
					print(f"     Population trend: {pop_trend}")
				
				threats = species.get('threats', [])
				if threats:
					print(f"     Number of threats documented: {len(threats)}")

def main():
	"""Main execution function."""
	
	print("IUCN Red List API - Bee Conservation Data Collection")
	print("\nThis script collects detailed conservation assessments for threatened bees.")
	print("\nData includes:")
	print("  - Conservation status and assessment details")
	print("  - Population trends")
	print("  - Documented threats")
	print("  - Habitat requirements")
	print("  - Conservation measures")
	print()
	
	# Create collector (add your token here or pass as parameter)
	collector = IUCNBeeData()
	
	# Collect all data
	collector.collect_all_bee_data()
	
	# Print summary
	collector.print_summary()
	
	# Save results if any
	if collector.results:
		collector.save_results()
	
	print("\n" + "=" * 70)
	print("DATA COLLECTION COMPLETE")
	print("=" * 70)
	print("\nNote: IUCN recommends 2-second delays between API calls.")
	print("This script respects those limits but may take some time to complete.")

if __name__ == "__main__":
	main()