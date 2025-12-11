# Wild Bee Conservation Statuses Around The World

## Description and Purpose
There is no one place where you can see a brief summary of all the wild bees that are endangered in the world. I am an amateur bee macrophotographer, so these kind of grievances upset me.

IUCN is the definitive organization, but they don't have data on every bee, and some conservation data is locked up regional/national/governmental organization/laboratories, and not tied to the international level at all. The overall goal of this codebase is to consolidate a single "profile" for every bee in the world, wherein one can see definitively, within the range of current available data as accurate as possible, what level of conservation the bee is at (threatened, extinct, least concern, etc) and other various details. There is no official website for now, just a collection of scripts located here. But the end goal would be like a searchable webpage (mostly usable by researchers and scientists, but ideally by the general public as well), sort of like a "Facebook profile" for native bees. At the moment, this is what I am collecting in my JSON files:

## Rough Schema of Bee Profile

### Existing fields
* Scientific Name
* Family Name
* Date and Location Last Observed (5 Most recent observations if available)
* Conservation Status (Statuses vary per organization, but generally the main ones are below is mostly taken from IUCN schema): [Listed in decreasing order of severity]
  + Extinct
  + Extinct in the wild
  + Critically Endangered
  + Endangered
  + Vulnerable
  + Near Threatened
  + Least Concern
  + Data Deficient
* Common Name (if available)
* Profile at the organization's URL


## Data Sources

* [Global Biodiversity Information Facility - GBIF](https://www.gbif.org/)
* [International Union for the Conservation of Nature - IUCN](https://www.iucnredlist.org/)
   + I have requested an IUCN api key but they have not granted me access yet. In the meantime, for European-specific data, I have collected data from this [PDF red list from 2014](https://portals.iucn.org/library/node/45219) myself.
* [INaturalist](https://www.inaturalist.org/)
   + Internally uses data from NS and IUCN, but mostly an amazing source for the specificity of observational and locational data.
* [NatureServe - NS](https://www.natureserve.org/)
  + Has data at more granular levels such as national, regional and geographical.
 
## Usage

Run each script (the lone `.py` file) locally in its own directory and it will populate the local json file accordingly with the relevant conservation data:

For example, for the NatureServe data:

```
dliddell@MacBook-Air-2 nature_serve % ls
natureserve_api_data.py	natureserve_bees.json
dliddell@MacBook-Air-2 nature_serve % python natureserve_api_data.py
```

## Next steps

* Make an actual bee profile that is an rough aggregate of all the data available for a specific bee.
* Build the backend first, then build a frontend to represent the profile of each bee.
* Possible fields to add for each bee:
  + Preferred flower genus, species, family.
  + Oligolectic or Polylectic (Specialist or Generalist pollinator)
  + Nesting preference (cavity, ground, mud, leaves, wood, stone)
  + Habitat
  + What else should I add?

