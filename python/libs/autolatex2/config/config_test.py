#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015  Stephane Galland <galland@arakhne.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.


import unittest
import logging
import os

from autolatex2.config.config import Config
from autolatex2.config.generation import GenerationConfig
from autolatex2.config.translator import TranslatorConfig

from autolatex2.utils import debug

########################################################
##
class ConfigMock(Config):
	def __init__(self, config : Config, *, isdir : bool):
		Config.__init__(self)
		self.__isDir = isdir
		self.osname = config.osname
		self.homedir = config.homedir

	def _isdir(self, directory : str) -> bool:
		return self.__isDir


########################################################
##
class TestPosixConfig(unittest.TestCase):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__config = None
		self.__dirname = None

	def setUp(self):
		logging.getLogger().setLevel(logging.CRITICAL)
		self.__dirname = os.path.dirname(os.path.realpath(__file__))
		self.__config = Config()
		self.__config.osname = 'posix'
		self.__config.homedir = os.path.join('', 'home')

	@property
	def config(self) -> Config:
		return self.__config

	@property
	def dirname(self) -> str:
		return self.__dirname



	def test_makeDocumentConfigFilename(self):
		filename = self.config.makeDocumentConfigFilename(self.dirname)
		self.assertEqual(os.path.join(self.dirname, '.autolatex_project.cfg'), filename)



	def test_userConfigDirectory(self):
		name = self.config.userConfigDirectory
		self.assertEqual(os.path.join('home', '.autolatex'), name)



	def test_userConfigFile_directory(self):
		self.__config = ConfigMock(self.__config, isdir = True)
		name = self.config.userConfigFile
		self.assertEqual(os.path.join('home', '.autolatex', 'autolatex.conf'), name)

	def test_userConfigFile_noDirectory(self):
		self.__config = ConfigMock(self.__config, isdir = False)
		name = self.config.userConfigFile
		self.assertEqual(os.path.join('home', '.autolatex'), name)



	def test_documentDirectory_getter(self):
		directory = self.config.documentDirectory
		self.assertIsNone(directory)

	def test_documentDirectory_setter(self):
		pass



	def test_installationDirectory(self):
		directory = self.config.installationDirectory
		expected = os.path.abspath(os.path.dirname(__file__))
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		self.assertEqual(expected, directory)



	def test_name_getter(self):
		self.assertIsNone(self.config.name)

	def test_name_setter(self):
		self.config.name = "myname"
		self.assertEqual("myname", self.config.name)



	def test_launchName_getter(self):
		self.assertIsNone(self.config.launchName)

	def test_launchName_setter(self):
		self.config.launchName = "myname"
		self.assertEqual("myname", self.config.launchName)



	def test_version(self):
		version = self.config.version
		self.assertEqual("36.0", version)



	def test_generation_getter(self):
		self.assertIsNotNone(self.config.generation)

	def test_generation_setter(self):
		g = GenerationConfig()
		self.config.generation = g
		self.assertEqual(g, self.config.generation)



	def test_translators_getter(self):
		self.assertIsNotNone(self.config.translators)

	def test_translators_setter(self):
		g = TranslatorConfig()
		self.config.translators = g
		self.assertEqual(g, self.config.translators)



########################################################
##
class TestNtConfig(unittest.TestCase):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__config = None
		self.__dirname = None

	def setUp(self):
		logging.getLogger().setLevel(logging.CRITICAL)
		self.__dirname = os.path.dirname(os.path.realpath(__file__))
		self.__config = Config()
		self.__config.osname = 'nt'
		self.__config.homedir = os.path.join('C:', 'home')

	@property
	def config(self) -> Config:
		return self.__config

	@property
	def dirname(self) -> str:
		return self.__dirname




	def test_makeDocumentConfigFilename(self):
		filename = self.config.makeDocumentConfigFilename(self.dirname)
		self.assertEqual(os.path.join(self.dirname, 'autolatex_project.cfg'), filename)



	def test_userConfigDirectory(self):
		name = self.config.userConfigDirectory
		self.assertEqual(os.path.join('C:', 'home', 'Local Settings', 'Application Data', 'autolatex'), name)



	def test_userConfigFile_directory(self):
		self.__config = ConfigMock(self.__config, isdir = True)
		name = self.config.userConfigFile
		self.assertEqual(os.path.join('C:', 'home', 'Local Settings', 'Application Data', 'autolatex', 'autolatex.conf'), name)

	def test_userConfigFile_noDirectory(self):
		self.__config = ConfigMock(self.__config, isdir = False)
		name = self.config.userConfigFile
		self.assertEqual(os.path.join('C:', 'home', 'Local Settings', 'Application Data', 'autolatex.conf'), name)



	def test_documentDirectory_getter(self):
		directory = self.config.documentDirectory
		self.assertIsNone(directory)

	def test_documentDirectory_setter(self):
		pass



	def test_installationDirectory(self):
		directory = self.config.installationDirectory
		expected = os.path.abspath(os.path.dirname(__file__))
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		self.assertEqual(expected, directory)



	def test_name_getter(self):
		self.assertIsNone(self.config.name)

	def test_name_setter(self):
		self.config.name = "myname"
		self.assertEqual("myname", self.config.name)



	def test_launchName_getter(self):
		self.assertIsNone(self.config.launchName)

	def test_launchName_setter(self):
		self.config.launchName = "myname"
		self.assertEqual("myname", self.config.launchName)



	def test_version(self):
		version = self.config.version
		self.assertEqual("36.0", version)



	def test_generation_getter(self):
		self.assertIsNotNone(self.config.generation)

	def test_generation_setter(self):
		g = GenerationConfig()
		self.config.generation = g
		self.assertEqual(g, self.config.generation)



	def test_translators_getter(self):
		self.assertIsNotNone(self.config.translators)

	def test_translators_setter(self):
		g = TranslatorConfig()
		self.config.translators = g
		self.assertEqual(g, self.config.translators)

########################################################
##
class TestOtherConfig(unittest.TestCase):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__config = None
		self.__dirname = None

	def setUp(self):
		logging.getLogger().setLevel(logging.CRITICAL)
		self.__dirname = os.path.dirname(os.path.realpath(__file__))
		self.__config = Config()
		self.__config.osname = 'otheros'
		self.__config.homedir = 'home'

	@property
	def config(self) -> Config:
		return self.__config

	@property
	def dirname(self) -> str:
		return self.__dirname




	def test_makeDocumentConfigFilename(self):
		filename = self.config.makeDocumentConfigFilename(self.dirname)
		self.assertEqual(os.path.join(self.dirname, 'autolatex_project.cfg'), filename)



	def test_userConfigDirectory(self):
		name = self.config.userConfigDirectory
		self.assertEqual(os.path.join('home', 'autolatex'), name)



	def test_userConfigFile_directory(self):
		self.__config = ConfigMock(self.__config, isdir = True)
		name = self.config.userConfigFile
		self.assertEqual(os.path.join('home', 'autolatex', 'autolatex.conf'), name)

	def test_userConfigFile_noDirectory(self):
		self.__config = ConfigMock(self.__config, isdir = False)
		name = self.config.userConfigFile
		self.assertEqual(os.path.join('home', 'autolatex.conf'), name)



	def test_documentDirectory_getter(self):
		directory = self.config.documentDirectory
		self.assertIsNone(directory)

	def test_documentDirectory_setter(self):
		pass



	def test_installationDirectory(self):
		directory = self.config.installationDirectory
		expected = os.path.abspath(os.path.dirname(__file__))
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		expected = os.path.dirname(expected)
		self.assertEqual(expected, directory)



	def test_name_getter(self):
		self.assertIsNone(self.config.name)

	def test_name_setter(self):
		self.config.name = "myname"
		self.assertEqual("myname", self.config.name)



	def test_launchName_getter(self):
		self.assertIsNone(self.config.launchName)

	def test_launchName_setter(self):
		self.config.launchName = "myname"
		self.assertEqual("myname", self.config.launchName)



	def test_version(self):
		version = self.config.version
		self.assertEqual("36.0", version)



	def test_generation_getter(self):
		self.assertIsNotNone(self.config.generation)

	def test_generation_setter(self):
		g = GenerationConfig()
		self.config.generation = g
		self.assertEqual(g, self.config.generation)



	def test_translators_getter(self):
		self.assertIsNotNone(self.config.translators)

	def test_translators_setter(self):
		g = TranslatorConfig()
		self.config.translators = g
		self.assertEqual(g, self.config.translators)




if __name__ == '__main__':
    unittest.main()

