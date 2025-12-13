# -*- coding: utf-8 -*-

# 
# mc-toolkit - generate_worth.py
# © 2020-2024 Vinyl Da.i'gyu-Kazotetsu [https://www.queengoob.org].
# This code is licensed under the GNU GPLv3 license (https://choosealicense.com/licenses/gpl-3.0/).
#
# Generate a worth.yml using some base values and recipes determined from Minecraft source
#

import argparse, os
from pathlib import Path

from DecompilerMC.main import get_latest_version
from lib import prepare_source, get_items, creative_only_items, Version

import yaml
try:
	from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
	from yaml import Loader, Dumper

script_dir = Path(os.path.dirname(__file__))
output_dir = script_dir / "output"

base_worth = yaml.load(open(script_dir / "base_worth.yml", 'r'), Loader=Loader)
new_base = {k: float(max(round(base_worth[k] * 1.65), 1)) for k in base_worth}
with open("round_worth.yml", "w") as file:
    yaml.dump(new_base, file)
base_worth = new_base
worth_header = open(script_dir / "worth_yml_header.yml", "r").read()

def remap_ingredient(item_id):
	remappings = {
		'PLANKS': 'OAK_PLANKS',
		'LOGS': 'OAK_LOG',
		'LOGS_THAT_BURN': 'OAK_LOG',
		'WOODEN_SLABS': 'OAK_SLAB',
		'COALS': 'COAL',
		'WOOL': 'WHITE_WOOL',
		'SOUL_FIRE_BASE_BLOCKS': 'SOUL_SOIL',
		'STONE_CRAFTING_MATERIALS': 'COBBLESTONE',
		'CHISELED_QUARTZ_BLOCK/QUARTZ_PILLAR': 'QUARTZ_PILLAR',
		'FURNACE_MATERIALS': 'COBBLESTONE',
		'WOODEN_FENCES': 'OAK_FENCE',
		'WOODEN_TOOL_MATERIALS': 'OAK_PLANKS',
		'STONE_TOOL_MATERIALS': 'COBBLESTONE',
		'IRON_TOOL_MATERIALS': 'IRON_INGOT',
		'GOLD_TOOL_MATERIALS': 'GOLD_INGOT',
		'DIAMOND_TOOL_MATERIALS': 'DIAMOND',
		'EGGS': 'EGG',
		'LEAVES': 'OAK_LEAVES'
	}

	if item_id in remappings:
		return remappings[item_id]

	if '/' in item_id:
		item_id = item_id.split('/')[0]
	elif item_id.endswith('_LOGS'):
		item_id = item_id.replace('_LOGS', '_LOG')
	elif item_id.endswith('_STEMS'):
		item_id = item_id.replace('_STEMS', '_STEM')
	elif item_id.endswith('_BLOCKS'):
		item_id = item_id.replace('_BLOCKS', '_BLOCK')

	return item_id


def add_to_worth(worth, item_id, value):
	worth[item_id] = float(max(round(value), 1))

# Calculate worth for a specific recipe
def calculate_worth_from_recipe(items, worth, item_id):
	recipe = items.get(item_id)
	if not recipe:
		if item_id not in items:
			raise Exception(f'Item {item_id} not found!')
		raise Exception(f'Item {item_id} has no recipe!')

	if type(recipe) == list:
		recipe = recipe[0]

	value = 0.0
	ing_count = 0

	for i, ic in recipe['ingredients'].items():
		ingredient = remap_ingredient(i)
		if ingredient not in worth:
			raise Exception(f"Ingredient {ingredient} is not defined in worth data!")
		value += worth[ingredient] * ic
		ing_count += ic

	result = value * (1.0 - ((ing_count - 1) / 100)) / recipe['count']

	if recipe['pattern'] in ['axe', 'shovel', 'hoe']:
		result = result * 0.9
	elif recipe['pattern'] in ['furnace', 'stonecutter']:
		result = result * 1.25
	elif recipe['pattern'] in ['brewing']:
		blaze_powder = remap_ingredient("BLAZE_POWDER")
		if blaze_powder not in worth:
			raise Exception(f"Ingredient {blaze_powder} is not defined in worth data!")
		result = result + worth[blaze_powder] / 20

	return result

def calculate_worth(worth, items):
	for item, recipe in items.items():

		if item in worth:
			continue # Skip already calculated values

		# Ores
		if item.endswith('_ORE'):
			material = item.replace("NETHER_", "").replace("DEEPSLATE_", "").split('_')[0]
			if material in ['IRON', 'COPPER', 'GOLD']:
				material = f'RAW_{material}'
			elif material == 'LAPIS':
				material = 'LAPIS_LAZULI'
			add_to_worth(worth, item, worth[material] * 0.75)
			continue

		# Oxidized copper blocks and doors
		elif item.startswith(("EXPOSED_COPPER", "WEATHERED_COPPER", "OXIDIZED_COPPER")):
			base_copper_item = "CUT_COPPER" if not "door" in item else ("COPPER_" + item.split("_COPPER_")[1])
			if not base_copper_item in worth:
				continue # Need to wait for calculation
			add_to_worth(worth, item, worth[base_copper_item] *
				(0.5 if item.startswith('EXPOSED') else 0.4 if item.startswith('WEATHERED') else 0.3)
			)
			continue

		# Damaged anvils (CHIPPED_ANVIL, DAMAGED_ANVIL)
		elif item.endswith("_ANVIL"):
			if not 'ANVIL' in worth:
				continue # Need to wait for calculation
			add_to_worth(worth, item, worth['ANVIL'] * (0.5 if item == 'CHIPPED_ANVIL' else 0.25))
			continue

		if not recipe:
			continue # No recipe, cannot calculate

		if type(recipe) == list:
			recipe = recipe[0]

		if recipe['pattern'] == 'brewing' and remap_ingredient("BLAZE_POWDER") not in worth:
			continue

		can_calc = True
		for ing in recipe['ingredients'].keys():
			if remap_ingredient(ing) not in worth:
				can_calc = False
				break

		if not can_calc:
			continue

		add_to_worth(worth, item, calculate_worth_from_recipe(items, worth, item))

		# Handle legacy names
		if item.startswith('END_STONE_BRICK') and item != "END_STONE_BRICKS":
			worth[item.replace('_BRICK', '')] = worth[item]
		elif item == "MELON":
			worth["MELON_BLOCK"] = worth['MELON']
		elif item == "SKULL_BANNER_PATTERN":
			worth["SKELETON_BANNER_PATTERN"] = worth["SKULL_BANNER_PATTERN"]

def remap_names_for_essentials(worth):
	new_worth = {}
	for item, value in worth.items():
		new_worth[item.replace('_', '').lower()] = value
	return new_worth


def get_opposite(potion_name):
	if potion_name == 'slowness':
		return ('swiftness', 'leaping')
	if potion_name == 'harming':
		return ('healing', 'poison')
	if potion_name == 'invisibility':
		return ('night_vision', )
	if potion_name == 'swiftness':
		return ('slowness', )
	if potion_name == 'leaping':
		return ('slowness', )
	if potion_name == 'healing':
		return ('harming', )
	if potion_name == 'poison':
		return ('harming', )
	if potion_name == 'night_vision':
		return ('invisibility', )
	return None


def add_potions(recipes):
	has_extended = ['regeneration', 'swiftness', 'fire_resistance', 'night_vision', 'strength', 'leaping', 'water_breathing', 'invisibility', 'slow_falling', 'poison', 'weakness', 'slowness', 'turtle_master']
	has_upgraded = ['regeneration', 'swiftness', 'healing', 'strength', 'leaping', 'poison', 'slowness', 'harming', 'turtle_master']

	# Simple potions
	potions = {}
	potions['water'] = []
	potions['awkward'] = [('POTION{potion:water}', 'NETHER_WART')]
	potions['mundane'] = [('POTION{potion:water}', 'REDSTONE')]
	potions['thick'] = [('POTION{potion:water}', 'GLOWSTONE_DUST')]
	potions['weakness'] = [('POTION{potion:water}', 'FERMENTED_SPIDER_EYE')]
	potions['swiftness'] = [('POTION{potion:awkward}', 'SUGAR')]
	potions['leaping'] = [('POTION{potion:awkward}', 'RABBIT_FOOT')]
	potions['healing'] = [('POTION{potion:awkward}', 'GLISTERING_MELON_SLICE')]
	potions['poison'] = [('POTION{potion:awkward}', 'SPIDER_EYE')]
	potions['water_breathing'] = [('POTION{potion:awkward}', 'PUFFERFISH')]
	potions['fire_resistance'] = [('POTION{potion:awkward}', 'MAGMA_CREAM')]
	potions['night_vision'] = [('POTION{potion:awkward}', 'GOLDEN_CARROT')]
	potions['strength'] = [('POTION{potion:awkward}', 'BLAZE_POWDER')]
	potions['regeneration'] = [('POTION{potion:awkward}', 'GHAST_TEAR')]
	potions['turtle_master'] = [('POTION{potion:awkward}', 'TURTLE_HELMET')]
	potions['slow_falling'] = [('POTION{potion:awkward}', 'PHANTOM_MEMBRANE')]
	potions['wind_charged'] = [('POTION{potion:awkward}', 'BREEZE_ROD')]
	potions['infested'] = [('POTION{potion:awkward}', 'STONE')]
	potions['weaving'] = [('POTION{potion:awkward}', 'COBWEB')]
	potions['oozing'] = [('POTION{potion:awkward}', 'SLIME_BLOCK')]

	# Inverted potions
	potions['slowness'] = [('POTION{potion:swiftness}', 'FERMENTED_SPIDER_EYE'),
						   ('POTION{potion:leaping}', 'FERMENTED_SPIDER_EYE')]
	potions['harming'] = [('POTION{potion:healing}', 'FERMENTED_SPIDER_EYE'),
						   ('POTION{potion:poison}', 'FERMENTED_SPIDER_EYE')]
	potions['invisibility'] = [('POTION{potion:night_vision}', 'FERMENTED_SPIDER_EYE')]

	for potion_name, potion_recipes in potions.items():
		full_name = 'POTION{potion:' + potion_name + '}'
		long_name = 'POTION{potion:long' + potion_name + '}'
		strong_name = 'POTION{potion:strong' + potion_name + '}'
		splash_name = 'SPLASH_' + full_name
		long_splash_name = 'SPLASH_' + long_name
		strong_splash_name = 'SPLASH_' + strong_name
		lingering_name = 'LINGERING_' + full_name
		long_lingering_name = 'LINGERING_' + long_name
		strong_lingering_name = 'LINGERING_' + strong_name
		full_tipped = 'TIPPED_ARROW{potion:' + potion_name + '}'
		long_tipped = 'TIPPED_ARROW{potion:long' + potion_name + '}'
		strong_tipped = 'TIPPED_ARROW{potion:strong' + potion_name + '}'

		opposite = get_opposite(potion_name)
		long_opposite_names = []
		long_opposite_splash = []
		long_opposite_lingering = []
		strong_opposite_names = []
		strong_opposite_splash = []
		strong_opposite_lingering = []
		if opposite is not None:
			long_opposite_names = ('POTION{potion:long' + name + '}' for name in opposite if name in has_extended)
			long_opposite_splash = ('SPLASH_POTION{potion:long' + name + '}' for name in opposite if name in has_extended)
			long_opposite_lingering = ('LINGERING_POTION{potion:long' + name + '}' for name in opposite if name in has_extended)
			strong_opposite_names = ('POTION{potion:strong' + name + '}' for name in opposite if name in has_upgraded)
			strong_opposite_splash = ('SPLASH_POTION{potion:strong' + name + '}' for name in opposite if name in has_upgraded)
			strong_opposite_lingering = ('LINGERING_POTION{potion:strong' + name + '}' for name in opposite if name in has_upgraded)

		if potion_name != 'water':
			recipes[full_name] = []
		recipes[splash_name] = []
		recipes[lingering_name] = []
		recipes[full_tipped] = {'count': 8, 'ingredients': {lingering_name: 1, "ARROW": 8}, 'pattern': [["ARROW", "ARROW", "ARROW"], ["ARROW", lingering_name, "ARROW"], ["ARROW", "ARROW", "ARROW"]]}
		if potion_name in has_extended:
			recipes[long_name] = []
			recipes[long_splash_name] = []
			recipes[long_lingering_name] = []
			recipes[long_tipped] = {'count': 8, 'ingredients': {long_lingering_name: 1, "ARROW": 8}, 'pattern': [["ARROW", "ARROW", "ARROW"], ["ARROW", long_lingering_name, "ARROW"], ["ARROW", "ARROW", "ARROW"]]}
		if potion_name in has_upgraded:
			recipes[strong_name] = []
			recipes[strong_splash_name] = []
			recipes[strong_lingering_name] = []
			recipes[strong_tipped] = {'count': 8, 'ingredients': {strong_lingering_name: 1, "ARROW": 8}, 'pattern': [["ARROW", "ARROW", "ARROW"], ["ARROW", strong_lingering_name, "ARROW"], ["ARROW", "ARROW", "ARROW"]]}
		for i in range(1, 4):
			for base_potion, ingredient in potion_recipes:
				recipes[full_name].append({'count': i, 'ingredients': {base_potion: i, ingredient: 1}, 'pattern': 'brewing'})
			recipes[splash_name].append({'count': i, 'ingredients': {full_name: i, 'GUNPOWDER': 1}, 'pattern': 'brewing'})
			recipes[lingering_name].append({'count': i, 'ingredients': {full_name: i, 'DRAGON_BREATH': 1}, 'pattern': 'brewing'})
			if potion_name in has_extended:
				recipes[long_name].append({'count': i, 'ingredients': {full_name: i, 'REDSTONE': 1}, 'pattern': 'brewing'})
				recipes[long_splash_name].append({'count': i, 'ingredients': {splash_name: i, 'REDSTONE': 1}, 'pattern': 'brewing'})
				recipes[long_lingering_name].append({'count': i, 'ingredients': {lingering_name: i, 'REDSTONE': 1}, 'pattern': 'brewing'})
				for opposite_name in long_opposite_names:
					recipes[long_name].append({'count': i, 'ingredients': {opposite_name: i, 'FERMENTED_SPIDER_EYE': 1}, 'pattern': 'brewing'})
				for opposite_name in long_opposite_splash:
					recipes[long_splash_name].append({'count': i, 'ingredients': {opposite_name: i, 'FERMENTED_SPIDER_EYE': 1}, 'pattern': 'brewing'})
				for opposite_name in long_opposite_lingering:
					recipes[long_lingering_name].append({'count': i, 'ingredients': {opposite_name: i, 'FERMENTED_SPIDER_EYE': 1}, 'pattern': 'brewing'})
			if potion_name in has_upgraded:
				recipes[strong_name].append({'count': i, 'ingredients': {full_name: i, 'GLOWSTONE_DUST': 1}, 'pattern': 'brewing'})
				recipes[strong_splash_name].append({'count': i, 'ingredients': {splash_name: i, 'GLOWSTONE_DUST': 1}, 'pattern': 'brewing'})
				recipes[strong_lingering_name].append({'count': i, 'ingredients': {lingering_name: i, 'GLOWSTONE_DUST': 1}, 'pattern': 'brewing'})
				for opposite_name in strong_opposite_names:
					recipes[strong_name].append({'count': i, 'ingredients': {opposite_name: i, 'FERMENTED_SPIDER_EYE': 1}, 'pattern': 'brewing'})
				for opposite_name in strong_opposite_splash:
					recipes[strong_splash_name].append({'count': i, 'ingredients': {opposite_name: i, 'FERMENTED_SPIDER_EYE': 1}, 'pattern': 'brewing'})
				for opposite_name in strong_opposite_lingering:
					recipes[strong_lingering_name].append({'count': i, 'ingredients': {opposite_name: i, 'FERMENTED_SPIDER_EYE': 1}, 'pattern': 'brewing'})


def generate_worth(mc_version, no_cache=False, outpath=output_dir / "worth.yml", essentials=True):
	source_path = prepare_source(mc_version)
	items = get_items(source_path, mc_version, no_cache)['items']
	add_potions(items)
	worth = base_worth

	calculated_items = len(worth.keys())
	while True:
		calculate_worth(worth, items)
		if len(worth.keys()) == calculated_items:
			break # We aren't able to calculate any more recipes
		calculated_items = len(worth.keys())

	for i in items:
		if i not in worth:
			print(f'{i} was not calculated!', f'Its recipe was {items[i]}' if items[i] else 'It has no recipe!')
		elif worth[i] == 0.0:
			print(f'{i} resulted in a value of 0.00, calculation error!')


	os.makedirs(output_dir, exist_ok=True)

	if essentials:
		worth = remap_names_for_essentials(worth)

	with open(outpath, 'w') as worthfile:
		worthfile.write(worth_header + "\n\n")
		worthfile.write(yaml.dump({'worth': worth}, Dumper=Dumper))

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog="generate_worth", description="Generate an EssentialsX worth.yml file based on Minecraft recipes and a few base prices")
	parser.add_argument('mc_version', nargs='?', default=get_latest_version()[1], help="The Minecraft version to use")
	parser.add_argument('-n', '--no_cache', action='store_true', help="Regenerate everything from scratch")
	parser.add_argument('-v', '--vanilla', action='store_true', help="Use vanilla item names, instead of the remappings EssentialsX wishes to use")
	args = parser.parse_args()

	generate_worth(Version(args.mc_version), no_cache=args.no_cache, essentials=not args.vanilla)
