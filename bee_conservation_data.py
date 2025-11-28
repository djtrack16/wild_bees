#!/usr/bin/env python3
"""
Script to collect endangered bee species data from IUCN Red List and iNaturalist APIs.
Requires: requests library (pip install requests)
"""

import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
import ipdb

class BeeConservationData:
	def __init__(self):
		self.iucn_base_url = "https://apiv3.iucnredlist.org/api/v3"
		self.inat_base_url = "https://api.inaturalist.org/v1"
		
		# You'll need to get a free API token from: https://apiv3.iucnredlist.org/api/v3/token
		self.iucn_token = "YOUR_IUCN_API_TOKEN_HERE"
		
		# Conservation statuses we're interested in (IUCN format)
		self.target_statuses = ['EX', 'EW', 'CR', 'EN', 'VU', 'NT']
		
		# iNaturalist uses different format: lowercase with underscores
		self.inat_status_map = {
			'extinct': 'EX',
			'extinct_in_the_wild': 'EW',
			'critically imperiled': 'CR', # critically endangered
			'endangered': 'EN',
			'vulnerable': 'VU',
			'VU': 'VU',
			'near threatened': 'NT'
		}
		
		self.results = []
	
	def search_iucn_bees(self) -> List[Dict]:
		"""
		Search IUCN Red List for bee species with threatened status.
		Note: IUCN uses 'Apoidea' superfamily, but we'll filter for actual bees (Anthophila).
		"""
		print("Querying IUCN Red List for bee species...")
		
		# First, we need to search by taxonomic group
		# IUCN doesn't have a direct "Anthophila" query, so we search Hymenoptera and filter
		endpoint = f"{self.iucn_base_url}/species/page/0"
		params = {
			'token': self.iucn_token
		}
		
		all_bee_species = []
		page = 0
		
		# Note: This is a simplified approach. In production, you'd want to:
		# 1. Use the taxonomy endpoint to get all bee species
		# 2. Or filter by specific bee families (Apidae, Megachilidae, Halictidae, etc.)
		
		try:
			# Get comprehensive species list endpoint
			search_endpoint = f"{self.iucn_base_url}/speciesgroup/Hymenoptera/page/{page}"
			
			response = requests.get(search_endpoint, params=params, timeout=30)
			
			if response.status_code == 200:
				data = response.json()
				
				# Filter for bees and target conservation statuses
				if 'result' in data:
					for species in data['result']:
						# Check if it's a bee (families: Apidae, Megachilidae, Halictidae, Andrenidae, Colletidae, Melittidae, Stenotritidae)
						# and has a threatened status
						if species.get('category') in self.target_statuses:
							# Additional filtering would check family names here
							all_bee_species.append({
								'scientific_name': species.get('scientific_name'),
								'common_name': species.get('main_common_name'),
								'iucn_status': species.get('category'),
								'taxonid': species.get('taxonid')
							})
			else:
				print(f"IUCN API Error: {response.status_code}")
				print("Note: You need to add your IUCN API token to use this script.")
				print("Get a free token at: https://apiv3.iucnredlist.org/api/v3/token")
				
		except requests.exceptions.RequestException as e:
			print(f"Error querying IUCN: {e}")
		
		return all_bee_species
	
	def get_iucn_species_details(self, taxonid: int) -> Optional[Dict]:
		"""Get detailed information for a specific species from IUCN."""
		endpoint = f"{self.iucn_base_url}/species/id/{taxonid}"
		params = {'token': self.iucn_token}
		
		try:
			response = requests.get(endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				return data.get('result', [{}])[0]
			time.sleep(0.5)  # Rate limiting
		except requests.exceptions.RequestException as e:
			print(f"Error getting species details: {e}")
		
		return None
	
	def search_inat_species(self, scientific_name: str) -> Optional[Dict]:
		"""
		Search iNaturalist for species observations and data.
		"""
		# First, get the taxon ID
		taxon_endpoint = f"{self.inat_base_url}/taxa"
		params = {
			'q': scientific_name,
			'rank': 'species',
			'is_active': 'true'
		}
		#ipdb.set_trace()
		try:
			response = requests.get(taxon_endpoint, params=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				results = data.get('results', [])
				
				if results:
					taxon = results[0]
					taxon_id = taxon.get('id')
					
					# Get recent observations
					obs_data = self.get_inat_observations(taxon_id, scientific_name)
					
					return (obs_data[0] if obs_data else {}) #{
						#'inat_taxon_id': taxon_id,
						#'observations_count': taxon.get('observations_count', 0),
						#'wikipedia_summary': taxon.get('wikipedia_summary'),
						#'recent_observations': obs_data
					#}
			
			time.sleep(0.3)  # Rate limiting for iNaturalist
			
		except requests.exceptions.RequestException as e:
			print(f"Error querying iNaturalist for {scientific_name}: {e}")
		
		return None
	
	def get_inat_observations(self, taxon_id: int, scientific_name: str, limit: int = 1) -> List[Dict]:
		"""Get recent observations for a species from iNaturalist."""
		obs_endpoint = f"{self.inat_base_url}/observations"
		params = {
			'taxon_id': taxon_id,
			'order': 'desc',
			'order_by': 'observed_on',
			'per_page': limit,
			'quality_grade': 'research'  # Only verified observations
		}
		
		try:
			response = requests.get(obs_endpoint, params=params, timeout=30)
			#ipdb.set_trace()
			if response.status_code == 200:
				data = response.json()
				observations = []
				
				for obs in data.get('results', []):
					observations.append({
						'date': obs.get('observed_on'),
						'location': obs.get('place_guess'),
						'latitude': obs.get('location', '').split(',')[0] if obs.get('location') else None,
						'longitude': obs.get('location', '').split(',')[1] if obs.get('location') else None,
						'observer': obs.get('user', {}).get('login'),
						'url': obs.get('uri')
					})
				return observations
				
		except requests.exceptions.RequestException as e:
			print(f"Error getting observations: {e}")
		
		return []
	
	def get_all_threatened_bees_inat(self) -> List[Dict]:
		"""
		Get all bee species with conservation status from iNaturalist.
		iNaturalist tracks IUCN conservation statuses in their taxonomy.
		"""
		print("Querying iNaturalist for threatened bee species...")
		
		all_bees = []
		
		# Major bee families to search
		bee_families = [
			'Apidae',         # Honey bees, bumble bees, carpenter bees, etc.
			'Megachilidae',   # Leafcutter and mason bees
			'Halictidae',     # Sweat bees
			'Andrenidae',     # Mining bees
			'Colletidae',     # Plasterer and masked bees
			'Melittidae',     # Melittid bees
			'Stenotritidae'   # Large Australian bees
		]
		
		for family in bee_families:
			print(f"  Searching family: {family}")
			
			# Search for species in this family with conservation status
			taxon_endpoint = f"{self.inat_base_url}/taxa"
			params = {
				'q': family,
				'rank': 'family',
				'is_active': 'true'
			}
			
			try:
				response = requests.get(taxon_endpoint, params=params, timeout=30)
				#ipdb.set_trace()
				if response.status_code == 200:
					data = response.json()
					results = data.get('results', [])
					
					if results:
						family_taxon_id = results[0].get('id')
						
						# Get all species in this family
						species_endpoint = f"{self.inat_base_url}/taxa"
						species_params = {
							'taxon_id': family_taxon_id,
							'rank': 'species',
							'per_page': 1000,
							'is_active': 'true'
						}
						
						species_response = requests.get(species_endpoint, params=species_params, timeout=30)
						if species_response.status_code == 200:
							#ipdb.set_trace()
							
							species_data = species_response.json()
							
							for taxon in species_data.get('results', []):
								#per_species_request = requests.get(species_endpoint, params={'taxon_id': 121519, 'rank': 'species', 'is_active': 'true'}, timeout=30)
								#ipdb.set_trace()
                # Check if species has conservation status
								# iNaturalist stores this in conservation_statuses array
								conservation_statuses = taxon.get('conservation_statuses', [])
								
								# Also check the simpler conservation_status field
								if not conservation_statuses:
									conservation_status = taxon.get('conservation_status')
									if conservation_status:
										conservation_statuses = [conservation_status]
								
								for status_obj in conservation_statuses:
									if isinstance(status_obj, dict):
										status_code = status_obj.get('status_name', '')
									else:
										# Sometimes it's just a string
										status_code = status_obj
									
									# Map iNat format to IUCN abbreviations
									iucn_code = self.inat_status_map.get(status_code)
									# Filter for our target statuses
									if isinstance(status_code, str):
										print(f"{taxon['name']} is {status_code}")
									
									if status_code:
										#print(iucn_code)
										result = {
											'scientific_name': taxon.get('name'),
											'common_name': taxon.get('preferred_common_name'),
											'family': family,
											'iucn_status': iucn_code,
											'inat_status': status_code,
											'inat_taxon_id': taxon.get('id'),
											'observations_count': taxon.get('observations_count', 0)
										}
										if taxon['extinct']:
											result['extinct'] = taxon['extinct']
											print('EXTINCT')
										all_bees.append(result)
										break  # Only add once per species
				
				time.sleep(0.5)  # Rate limiting
				
			except requests.exceptions.RequestException as e:
				print(f"Error querying {family}: {e}")
		
		return all_bees
	
		"""Main function to collect all bee conservation data."""
		print("=" * 60)
		print("ENDANGERED BEE SPECIES DATA COLLECTION")
		print("=" * 60)
		print()
		
		# Step 1: Get IUCN bee species
		iucn_species = self.search_iucn_bees()
		print(f"\nFound {len(iucn_species)} bee species with conservation status on IUCN")
		print()
		
		# Step 2: Enrich each species with additional data
		for i, species in enumerate(iucn_species, 1):
			print(f"Processing {i}/{len(iucn_species)}: {species['scientific_name']}...")
			
			# Get detailed IUCN info
			if species.get('taxonid'):
				iucn_details = self.get_iucn_species_details(species['taxonid'])
				if iucn_details:
					species['population_trend'] = iucn_details.get('population_trend')
					species['habitat'] = iucn_details.get('habitat')
			
			# Get iNaturalist data
			inat_data = self.search_inat_species(species['scientific_name'])
			if inat_data:
				species['inat_data'] = inat_data
			
			self.results.append(species)
			
			# Rate limiting
			time.sleep(1)
		
		return self.results
	
	def save_results(self, filename: str = 'endangered_bees.json'):
		"""Save results to a JSON file."""
		output = {
			'collection_date': datetime.now().isoformat(),
			'total_species': len(self.results),
			'species': self.results
		}
		
		with open(filename, 'w', encoding='utf-8') as f:
			json.dump(output, f, indent=2, ensure_ascii=False)
		
		print(f"\n✓ Results saved to {filename}")
	
	def print_summary(self):
		"""Print a summary of collected data."""
		print("\n" + "=" * 60)
		print("SUMMARY")
		print("=" * 60)
		
		status_counts = {}
		for species in self.results:
			status = species.get('iucn_status', 'Unknown')
			status_counts[status] = status_counts.get(status, 0) + 1
		
		print(f"\nTotal species found: {len(self.results)}")
		print("\nBy conservation status:")
		for status in ['EX', 'EW', 'CR', 'EN', 'VU', 'NT']:
			count = status_counts.get(status, 0)
			if count > 0:
				print(f"  {status}: {count}")
		
		# Show species with recent iNaturalist observations
		with_obs = [s for s in self.results if s.get('inat_data', {}).get('observations_count', 0) > 0]
		print(f"\nSpecies with iNaturalist observations: {len(with_obs)}")

def main():
	"""Main execution function."""
	collector = BeeConservationData()
	
	# For now, use iNaturalist only (no IUCN token required)
	print("=" * 60)
	print("ENDANGERED BEE SPECIES DATA COLLECTION (iNaturalist)")
	print("=" * 60)
	print()
	
	# Get all bee species from iNaturalist with conservation status
	bee_species = collector.get_all_threatened_bees_inat()
	
	print(f"\nFound {len(bee_species)} bee species with conservation status")
	print()
	
	# Collect detailed data for each species
	for i, species in enumerate(bee_species, 1):
		print(f"Processing {i}/{len(bee_species)}: {species['scientific_name']}...")
		
		inat_data = collector.search_inat_species(species['scientific_name'])
		if inat_data:
			species['most_recent_observation'] = inat_data
		
		collector.results.append(species)
		time.sleep(0.5)  # Rate limiting
	
	# Save and display results
	collector.save_results()
	collector.print_summary()
	
	print("\n✓ Data collection complete!")
	print("\nNext steps:")
	print("1. Review endangered_bees.json")
	print("2. Add IUCN API token for official conservation statuses")
	print("3. Add GBIF queries for more occurrence data")

if __name__ == "__main__":
	main()