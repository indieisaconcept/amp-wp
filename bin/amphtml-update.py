"""
This script is used to generate the 'class-amp-allowed-tags-generated.php'
file that is used by the class AMP_Tag_And_Attribute_Sanitizer.

Follow the steps below to generate a new version of the allowed tags class:

- Download a copy of the latet AMPHTML repository from github:

	git clone git@github.com:ampproject/amphtml.git

- Copy this file into the repo's validator subdirectory:

	cp amp_wp_build.py amphtml/validator

- Run the file from the validator subdirectory:
	cd amphtml/validator;python amp_wp_build.py

- The class-amp-allowed-tags-generated.php will be generated at:
	amphtml/validator/amp_wp/class-amp-allowed-tags-generated.php

- copy this file into the amp-wp plugin:
	cp amp_wp/class-amp-allowed-tags-generated.php /path/to/wordpress/wp-content/plugins/amp-wp/includes/sanitizers/

Then have fun sanitizing your AMP posts!
"""

import glob
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import collections

def Die(msg):
		print >> sys.stderr, msg
		sys.exit(1)


def SetupOutDir(out_dir):
	"""Sets up a clean output directory.

	Args:
		out_dir: directory name of the output directory. Must not have slashes,
			dots, etc.
	"""
	logging.info('entering ...')
	assert re.match(r'^[a-zA-Z_\-0-9]+$', out_dir), 'bad out_dir: %s' % out_dir

	if os.path.exists(out_dir):
		subprocess.check_call(['rm', '-rf', out_dir])
	os.mkdir(out_dir)
	logging.info('... done')


def GenValidatorPb2Py(out_dir):
	"""Calls the proto compiler to generate validator_pb2.py.

	Args:
		out_dir: directory name of the output directory. Must not have slashes,
			dots, etc.
	"""
	logging.info('entering ...')
	assert re.match(r'^[a-zA-Z_\-0-9]+$', out_dir), 'bad out_dir: %s' % out_dir

	subprocess.check_call(['protoc', 'validator.proto',
												 '--python_out=%s' % out_dir])
	open('%s/__init__.py' % out_dir, 'w').close()
	logging.info('... done')


def GenValidatorProtoascii(out_dir):
	"""Assembles the validator protoascii file from the main and extensions.

	Args:
		out_dir: directory name of the output directory. Must not have slashes,
			dots, etc.
	"""
	logging.info('entering ...')
	assert re.match(r'^[a-zA-Z_\-0-9]+$', out_dir), 'bad out_dir: %s' % out_dir

	protoascii_segments = [open('validator-main.protoascii').read()]
	extensions = glob.glob('extensions/*/validator-*.protoascii')
	# In the Github project, the extensions are located in a sibling directory
	# to the validator rather than a child directory.
	if not extensions:
		extensions = glob.glob('../extensions/*/validator-*.protoascii')
	extensions.sort()
	for extension in extensions:
		protoascii_segments.append(open(extension).read())
	f = open('%s/validator.protoascii' % out_dir, 'w')
	f.write(''.join(protoascii_segments))
	f.close()

	logging.info('... done')


def GeneratePHP(out_dir):
	"""Generates PHP for WordPress AMP plugin to consume.

	Args:
		out_dir: directory name of the output directory. Must not have slashes,
			dots, etc.
	"""
	logging.info('entering ...')
	assert re.match(r'^[a-zA-Z_\-0-9]+$', out_dir), 'bad out_dir: %s' % out_dir

	allowed_tags, attr_lists, versions = ParseRules(out_dir)

	#Generate the output
	out = []
	GenerateHeaderPHP(out)
	GenerateSpecVersionPHP(out, versions)
	GenerateAllowedTagsPHP(out, allowed_tags)
	GenerateLayoutAttributesPHP(out, attr_lists)
	GenerateGlobalAttributesPHP(out, attr_lists)
	GenerateFooterPHP(out)

	# join out array into a single string and remove unneeded whitespace
	output = re.sub("\\(\\s*\\)", "()", '\n'.join(out))

	# replace 'True' with true and 'False' with false
	output = re.sub("'True'", "true", output)
	output = re.sub("'False'", "false", output)

	# Write the php file to disk.
	f = open('%s/class-amp-allowed-tags-generated.php' % out_dir, 'w')
	# f.write('\n'.join(out))
	f.write(output)
	f.close()
	logging.info('... done')


def GenerateHeaderPHP(out):
	logging.info('entering ...')

	# Output the file's header
	out.append('<?php')
	out.append('/**')
	out.append(' * Generated by %s - do not edit.' %
						 os.path.basename(__file__))
	out.append(' *')
	out.append(' * This is a list of HTML tags and attributes that are allowed by the')
	out.append(' * AMP specification. Note that tag names have been converted to lowercase.')
	out.append(' *')
	out.append(' * Note: This file only contains tags that are relevant to the `body` of')
	out.append(' * an AMP page. To include additional elements modify the variable')
	out.append(' * `mandatory_parent_blacklist` in the amp_wp_build.py script.')
	out.append(' *')
	out.append(' * phpcs:ignoreFile')
	out.append(' */')
	out.append('class AMP_Allowed_Tags_Generated {')
	out.append('')
	logging.info('... done')


def GenerateSpecVersionPHP(out, versions):
	logging.info('entering ...')

	# Output the version of the spec file and matching validator version
	if versions['spec_file_revision']:
		out.append('\tprivate static $spec_file_revision = %d;' % versions['spec_file_revision'])
	if versions['min_validator_revision_required']:
		out.append('\tprivate static $minimum_validator_revision_required = %d;' %
							 versions['min_validator_revision_required'])
	logging.info('... done')


def GenerateAllowedTagsPHP(out, allowed_tags):
	logging.info('entering ...')

  # Output the allowed tags dictionary along with each tag's allowed attributes
	out.append('')
	out.append('\tprivate static $allowed_tags = array(')
	sorted_tags = sorted(allowed_tags.items())
	for (tag, attributes_list) in collections.OrderedDict(sorted_tags).iteritems():
		GenerateTagPHP(out, tag, attributes_list)
	out.append('\t);')
	logging.info('... done')


def GenerateLayoutAttributesPHP(out, attr_lists):
	logging.info('entering ...')

	# Output the attribute list allowed for layouts.
	out.append('')
	out.append('\tprivate static $layout_allowed_attrs = array(')
	GenerateAttributesPHP(out, attr_lists['$AMP_LAYOUT_ATTRS'], 2)
	out.append('\t);')
	out.append('')
	logging.info('... done')


def GenerateGlobalAttributesPHP(out, attr_lists):
	logging.info('entering ...')

	# Output the globally allowed attribute list.
	out.append('')
	out.append('\tprivate static $globally_allowed_attrs = array(')
	GenerateAttributesPHP(out, attr_lists['$GLOBAL_ATTRS'], 2)
	out.append('\t);')
	out.append('')
	logging.info('... done')


def GenerateTagPHP(out, tag, attributes_list):
	logging.info('generating php for tag: %s...' % tag.lower())

	# Output an attributes list for a tag
	out.append('\t\t\'%s\' => array(' % tag.lower())
	for attributes in attributes_list:
		out.append('\t\t\tarray(')
		GenerateAttributesPHP(out, attributes)
		out.append('\t\t\t),')
	out.append('\t\t),')
	logging.info('... done with: %s' % tag.lower())


def GenerateAttributesPHP(out, attributes, indent_level = 4):
	logging.info('entering ...')

	indent = ''
	for i in range(0,indent_level):
		indent += '\t'

	sorted_attributes = sorted(attributes.items())
	for (attribute, values) in collections.OrderedDict(sorted_attributes).iteritems():
		logging.info('generating php for attribute: %s...' % attribute.lower())
		out.append('%s\'%s\' => array(' % (indent, attribute.lower()))
		GeneratePropertiesPHP(out, values)
		out.append('%s),' % indent)
		logging.info('...done with: %s' % attribute.lower())

	out.append('')
	logging.info('... done')


def GeneratePropertiesPHP(out, properties, indent_level = 5):
	logging.info('entering ...')

	indent = ''
	for i in range(0,indent_level):
		indent += '\t'

	sorted_properties = sorted(properties.items())
	for (prop, values) in collections.OrderedDict(sorted_properties).iteritems():
		logging.info('generating php for property: %s...' % prop.lower())
		if isinstance(values, (unicode, str, bool)):
			if isinstance(values, (unicode, str) ) and prop in ( 'mandatory_parent', 'mandatory_ancestor', 'mandatory_ancestor_suggested_alternative' ):
				values = values.lower()
			out.append('%s\'%s\' => \'%s\',' % (indent, prop.lower(), values))
		elif isinstance(values, (int)):
			out.append('%s\'%s\' => %d,' % (indent, prop.lower(), values))
		else:
			out.append('%s\'%s\' => array(' % (indent, prop.lower()))
			sorted_values = sorted(values.items())
			for(key, value) in collections.OrderedDict(sorted_values).iteritems():
				if isinstance(value, (unicode, str, bool)):
					out.append('%s\t\'%s\' => \'%s\',' % (indent, key, value))
				elif isinstance(value, (int)):
					out.append('%s\t\'%s\' => %d,' % (indent, key, value))
				else:
					GenerateValuesPHP(out, value)
			out.append('%s),' % indent)
		logging.info('...done with: %s' % prop.lower())

	logging.info('...done')


def GenerateValuesPHP(out, values, indent_level = 6):
	logging.info('entering...')

	indent = ''
	for i in range(0, indent_level):
		indent += '\t'

	if isinstance(values, dict):
		sorted_values = sorted(values.items())
		for (key, value) in collections.OrderedDict(sorted_values).iteritems():

			logging.info('generating php for value: %s...' % key.lower())

			if isinstance(value, (str, bool, unicode)):
				out.append('%s\'%s\' => \'%s\',' % (indent, key.lower(), value))

			elif isinstance(value, (int)):
				out.append('%s\'%s\' => %d,' % (indent, key.lower(), value))

			else:
				out.append('%s\'%s\' => array(' % (indent, key.lower()))
				sorted_value = sorted(value)
				for v in sorted_value:
					out.append('%s\t\'%s\',' % (indent, v))
				out.append('%s),' % indent)

			logging.info('...done with: %s' % key.lower())

	elif isinstance(values, list):
		sorted_values = sorted(values)
		for v in sorted_values:
			logging.info('generating php for value: %s' % v.lower())
			out.append('%s\t\'%s\',' % (indent, v.lower()))
			logging.info('...done with: %s' % v.lower())

	logging.info('...done')


def GenerateFooterPHP(out):
	logging.info('entering ...')

	# Output the footer.
	out.append('''
	/**
	 * Get allowed tags.
	 *
	 * @since 0.5
	 * @return array Allowed tags.
	 */
	public static function get_allowed_tags() {
		return self::$allowed_tags;
	}

	/**
	 * Get allowed tag.
	 *
	 * Get the rules for a single tag so that the entire data structure needn't be passed around.
	 *
	 * @since 0.7
	 * @param string $node_name Tag name.
	 * @return array|null Allowed tag, or null if the tag does not exist.
	 */
	public static function get_allowed_tag( $node_name ) {
		if ( isset( self::$allowed_tags[ $node_name ] ) ) {
			return self::$allowed_tags[ $node_name ];
		}
		return null;
	}

	/**
	 * Get list of globally-allowed attributes.
	 *
	 * @since 0.5
	 * @return array Allowed tag.
	 */
	public static function get_allowed_attributes() {
		return self::$globally_allowed_attrs;
	}

	/**
	 * Get layout attributes.
	 *
	 * @since 0.5
	 * @return array Allowed tag.
	 */
	public static function get_layout_attributes() {
		return self::$layout_allowed_attrs;
	}''')

	out.append('')

	out.append('}')
	out.append('')

	logging.info('... done')


def ParseRules(out_dir):
	logging.info('entering ...')

	# These imports happen late, within this method because they don't necessarily
	# exist when the module starts running, and the ones that probably do
	# are checked by CheckPrereqs.
	from google.protobuf import text_format
	from amp_wp import validator_pb2

	allowed_tags = {}
	attr_lists = {}
	versions = {}

	specfile='%s/validator.protoascii' % out_dir

	validator_pb2=validator_pb2
	text_format=text_format

	# Merge specfile with message buffers.
	rules = validator_pb2.ValidatorRules()
	text_format.Merge(open(specfile).read(), rules)

	# Record the version of this specfile and the corresponding validator version.
	if rules.HasField('spec_file_revision'):
		versions['spec_file_revision'] = rules.spec_file_revision

	if rules.HasField('min_validator_revision_required'):
		versions['min_validator_revision_required'] = rules.min_validator_revision_required

	# Build a dictionary of the named attribute lists that are used by multiple tags.
	for (field_desc, field_val) in rules.ListFields():
		if 'attr_lists' == field_desc.name:
			for attr_spec in field_val:
				attr_lists[UnicodeEscape(attr_spec.name)] = GetAttrs(attr_spec.attrs)

	# Build a dictionary of allowed tags and an associated list of their allowed
	# attributes, values and other criteria.

	# Don't include tags that have a mandatory parent with one of these tag names
	# since we're only concerned with using this tag list to validate the HTML
	# of the DOM
	mandatory_parent_blacklist = [
		'$ROOT',
		'!DOCTYPE',
	]

	for (field_desc, field_val) in rules.ListFields():
		if 'tags' == field_desc.name:
			for tag_spec in field_val:

				# Ignore tags that are outside of the body
				if tag_spec.HasField('mandatory_parent') and tag_spec.mandatory_parent in mandatory_parent_blacklist and tag_spec.tag_name != 'HTML':
					continue

				# Ignore the special $REFERENCE_POINT tag
				if '$REFERENCE_POINT' == tag_spec.tag_name:
					continue

				# Ignore deprecated tags
				if tag_spec.HasField('deprecation'):
					continue

				# If we made it here, then start adding the tag_spec
				if tag_spec.tag_name not in allowed_tags:
					tag_list = []
				else:
					tag_list = allowed_tags[UnicodeEscape(tag_spec.tag_name)]
				# AddTag(allowed_tags, tag_spec, attr_lists)

				gotten_tag_spec = GetTagSpec(tag_spec, attr_lists)
				if gotten_tag_spec is not None:
					tag_list.append(gotten_tag_spec)
					allowed_tags[UnicodeEscape(tag_spec.tag_name)] = tag_list

	logging.info('... done')
	return allowed_tags, attr_lists, versions


def GetTagSpec(tag_spec, attr_lists):
	logging.info('entering ...')

	tag_dict = GetTagRules(tag_spec)
	if tag_dict is None:
		return None
	attr_dict = GetAttrs(tag_spec.attrs)

	# Now add attributes from any attribute lists to this tag.
	for (tag_field_desc, tag_field_val) in tag_spec.ListFields():
		if 'attr_lists' == tag_field_desc.name:
			for attr_list in tag_field_val:
				attr_dict.update(attr_lists[UnicodeEscape(attr_list)])

	logging.info('... done')
	tag_spec_dict = {'tag_spec':tag_dict, 'attr_spec_list':attr_dict}
	if tag_spec.HasField('cdata'):
		cdata_dict = {}
		for (field_descriptor, field_value) in tag_spec.cdata.ListFields():
			if isinstance(field_value, (unicode, str, bool, int)):
				cdata_dict[ field_descriptor.name ] = field_value
			else:
				if hasattr( field_value, '_values' ):
					cdata_dict[ field_descriptor.name ] = {}
					for _value in field_value._values:
						for (key,val) in _value.ListFields():
							cdata_dict[ field_descriptor.name ][ key.name ] = val
		if len( cdata_dict ) > 0:
			tag_spec_dict['cdata'] = cdata_dict

	return tag_spec_dict


def GetTagRules(tag_spec):
	logging.info('entering ...')

	tag_rules = {}

	if hasattr(tag_spec, 'also_requires_tag') and tag_spec.also_requires_tag:
		also_requires_tag_list = []
		for also_requires_tag in tag_spec.also_requires_tag:
			also_requires_tag_list.append(UnicodeEscape(also_requires_tag))
		tag_rules['also_requires_tag'] = {'also_requires_tag': also_requires_tag_list}

	if hasattr(tag_spec, 'requires_extension') and len( tag_spec.requires_extension ) != 0:
		requires_extension_list = []
		for requires_extension in tag_spec.requires_extension:
			requires_extension_list.append(requires_extension)
		tag_rules['requires_extension'] = {'requires_extension': requires_extension_list}

	if hasattr(tag_spec, 'also_requires_tag_warning') and len( tag_spec.also_requires_tag_warning ) != 0:
		also_requires_tag_warning_list = []
		for also_requires_tag_warning in tag_spec.also_requires_tag_warning:
			also_requires_tag_warning_list.append(also_requires_tag_warning)
		tag_rules['also_requires_tag_warning'] = {'also_requires_tag_warning': also_requires_tag_warning_list}

	if tag_spec.disallowed_ancestor:
		disallowed_ancestor_list = []
		for disallowed_ancestor in tag_spec.disallowed_ancestor:
			disallowed_ancestor_list.append(UnicodeEscape(disallowed_ancestor))
		tag_rules['disallowed_ancestor'] = {'disallowed_ancestor': disallowed_ancestor_list}

	if tag_spec.html_format:
		html_format_list = []
		has_amp_format = False
		for html_format in tag_spec.html_format:
			if 1 == html_format:
				has_amp_format = True
		if not has_amp_format:
			return None

	if tag_spec.HasField('extension_spec'):
		extension_spec = {}
		for field in tag_spec.extension_spec.ListFields():
			extension_spec[ field[0].name ] = field[1]
		tag_rules['extension_spec'] = {'extension_spec':extension_spec}

	if tag_spec.HasField('mandatory'):
		tag_rules['mandatory'] = tag_spec.mandatory

	if tag_spec.HasField('mandatory_alternatives'):
		tag_rules['mandatory_alternatives'] = UnicodeEscape(tag_spec.mandatory_alternatives)

	if tag_spec.HasField('mandatory_ancestor'):
		tag_rules['mandatory_ancestor'] = UnicodeEscape(tag_spec.mandatory_ancestor)

	if tag_spec.HasField('mandatory_ancestor_suggested_alternative'):
		tag_rules['mandatory_ancestor_suggested_alternative'] = UnicodeEscape(tag_spec.mandatory_ancestor_suggested_alternative)

	if tag_spec.HasField('mandatory_parent'):
		tag_rules['mandatory_parent'] = UnicodeEscape(tag_spec.mandatory_parent)

	if tag_spec.HasField('spec_name'):
		tag_rules['spec_name'] = UnicodeEscape(tag_spec.spec_name)

	if tag_spec.HasField('spec_url'):
		tag_rules['spec_url'] = UnicodeEscape(tag_spec.spec_url)

	if tag_spec.HasField('unique'):
		tag_rules['unique'] = tag_spec.unique

	if tag_spec.HasField('unique_warning'):
		tag_rules['unique_warning'] = tag_spec.unique_warning



	logging.info('... done')
	return tag_rules


def GetAttrs(attrs):
	logging.info('entering ...')

	attr_dict = {}
	for attr_spec in attrs:

		value_dict = GetValues(attr_spec)

		# Add attribute name and alternative_names
		attr_dict[UnicodeEscape(attr_spec.name)] = value_dict

	logging.info('... done')
	return attr_dict


def GetValues(attr_spec):
	logging.info('entering ...')

	value_dict = {}

	# Add alternative names
	if attr_spec.alternative_names:
		alt_names_list = []
		for alternative_name in attr_spec.alternative_names:
			alt_names_list.append(UnicodeEscape(alternative_name))
		value_dict['alternative_names'] = {'alternative_names': alt_names_list}

	# Add blacklisted value regex
	if attr_spec.HasField('blacklisted_value_regex'):
		value_dict['blacklisted_value_regex'] = UnicodeEscape(attr_spec.blacklisted_value_regex)

	# dispatch_key is an int
	if attr_spec.HasField('dispatch_key'):
		value_dict['dispatch_key'] = attr_spec.dispatch_key

	# mandatory is a boolean
	if attr_spec.HasField('mandatory'):
		value_dict['mandatory'] = attr_spec.mandatory

	# Add allowed value
	if attr_spec.HasField('value'):
		value_dict['value'] = UnicodeEscape(attr_spec.value)

	# value_casei
	if attr_spec.HasField('value_casei'):
		value_dict['value_casei'] = UnicodeEscape(attr_spec.value_casei)

	# value_regex
	if attr_spec.HasField('value_regex'):
		value_dict['value_regex'] = UnicodeEscape(attr_spec.value_regex)

	# value_regex_casei
	if attr_spec.HasField('value_regex_casei'):
		value_dict['value_regex_casei'] = UnicodeEscape(attr_spec.value_regex_casei)

	#value_properties is a dictionary of dictionaries
	if attr_spec.HasField('value_properties'):
		value_properties_dict = {}
		for (value_properties_key, value_properties_val) in attr_spec.value_properties.ListFields():
			for value_property in value_properties_val:
				property_dict = {}
				# print 'value_property.name: %s' % value_property.name
				for (key,val) in value_property.ListFields():
					if val != value_property.name:
						if isinstance(val, unicode):
							val = UnicodeEscape(val)
						property_dict[UnicodeEscape(key.name)] = val
				value_properties_dict[UnicodeEscape(value_property.name)] = property_dict
		value_dict['value_properties'] = value_properties_dict

	# value_url is a dictionary
	if attr_spec.HasField('value_url'):
		value_url_dict = {}
		for (value_url_key, value_url_val) in attr_spec.value_url.ListFields():
			if isinstance(value_url_val, (list, collections.Sequence)):
				value_url_val_val = []
				for val in value_url_val:
					value_url_val_val.append(UnicodeEscape(val))
			else:
				value_url_val_val = value_url_val
			value_url_dict[value_url_key.name] = value_url_val_val
		value_dict['value_url'] = value_url_dict

	logging.info('... done')
	return value_dict


def UnicodeEscape(string):
	"""Helper function which escapes unicode characters.

	Args:
		string: A string which may contain unicode characters.
	Returns:
		An escaped string.
	"""
	return ('' + string).encode('unicode-escape')


def Main():
	"""The main method, which executes all build steps and runs the tests."""
	logging.basicConfig(
			format='[[%(filename)s %(funcName)s]] - %(message)s', level=logging.INFO)

	out_dir = 'amp_wp'

	SetupOutDir(out_dir)
	GenValidatorProtoascii(out_dir)
	GenValidatorPb2Py(out_dir)
	GenValidatorProtoascii(out_dir)
	GeneratePHP(out_dir)

if __name__ == '__main__':
	Main()
