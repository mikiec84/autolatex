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

from autolatex2.tex.utils import *

from autolatex2.utils import debug

class TestUtils(unittest.TestCase):

	def setUp(self):
		logging.getLogger().setLevel(logging.CRITICAL)



	def test_getTeXFileExtensions(self):
		self.assertEqual(('.tex', '.latex', '.ltx'), getTeXFileExtensions())

	def test_isTeXFileExtension(self):
		self.assertTrue(isTeXFileExtension('.tex'))
		self.assertTrue(isTeXFileExtension('.latex'))
		self.assertTrue(isTeXFileExtension('.ltx'))
		self.assertTrue(isTeXFileExtension('.TeX'))
		self.assertTrue(isTeXFileExtension('.LaTeX'))
		self.assertFalse(isTeXFileExtension('.doc'))

	def test_isTeXdocument(self):
		self.assertTrue(isTeXDocument('file.tex'))
		self.assertTrue(isTeXDocument('file.latex'))
		self.assertTrue(isTeXDocument('file.ltx'))
		self.assertTrue(isTeXDocument('file.TeX'))
		self.assertTrue(isTeXDocument('file.LaTeX'))
		self.assertFalse(isTeXDocument('file.doc'))






if __name__ == '__main__':
    unittest.main()

