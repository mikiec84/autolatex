# autolatex/__init__.py
# Copyright (C) 2013  Stephane Galland <galland@arakhne.org>
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

#---------------------------------
# IMPORTS
#---------------------------------

# Import standard python libs
import os
import subprocess
import tempfile
import re
# Try to use the threading library if it is available
try:
    import threading as _threading
except ImportError:
    import dummy_threading as _threading
# Include the Glib, Gtk and Gedit libraries
from gi.repository import GObject, Gtk, Gio, GdkPixbuf, Gedit, PeasGtk

# AutoLaTeX internal libs
from .utils import utils, gsettings
from .config.cli import window as cli_config
from .config.plugin import main_panel as plugin_config
from .widgets import error_console

#---------------------------------
# INTERNATIONALIZATION
#---------------------------------

import gettext
_T = gettext.gettext
utils.init_internationalization()

#---------------------------------
# CLASS _AutoLaTeXExecutionThread
#---------------------------------

# Launch AutoLaTeX inside a thread, and wait for the result
class _AutoLaTeXExecutionThread(_threading.Thread):
    # caller is an instance of AutoLaTeXPlugin
    # label is the text to display in the info bar. If none, there is no info bar.
    # gsettings is the object that permits to access to the Gsettings
    # directory is the path to set as the current path
    # directive is the AutoLaTeX command
    # params are the CLI options for AutoLaTeX
    def __init__(self, caller, label, gsettings, directory, directive, params):
	_threading.Thread.__init__(self)
	self.daemon = True
	self._enable_info_bar = gsettings.get_progress_info_visibility()
	self._caller = caller
	self._is_action_canceled = False
	self._info_bar_label = label
	self._info_bar = None
	self._sig_info_bar = 0
	self._directory = directory
	self._cmd = [utils.AUTOLATEX_BINARY] + params
	if directive:
		self._cmd.append(directive)

    # Run the thread
    def run(self):
	self._is_action_canceled = False
	progress_line_pattern = None

	# Test if the progress info must be shown
	activate_progress = (self._enable_info_bar and self._info_bar_label is not None)

	if activate_progress:
		# Add the info bar the inside of the Gtk thread
		GObject.idle_add(self._add_info_bar)
		# Updat the command line to obtain the progress data
		self._cmd.append('--progress=n')
		# Compile a regular expression to extract the progress amount
		progress_line_pattern = re.compile("^\\[\\s*([0-9]+)\\%\\]\\s+[#.]+(.*)$")

	# Launch the subprocess
	os.chdir(self._directory)
	process = subprocess.Popen(self._cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output = ''
	if process:
	    if activate_progress:
		# Use the info bar to draw the progress of the task
		process.poll()
		# Loop until the subprocess is dead
		while process.returncode is None and not self._is_action_canceled:
			if not process.stdout.closed:
				# Read a line from STDOUT and extract the progress amount
				process.stdout.flush()
				line = process.stdout.readline()
				if line:
					mo = re.match(progress_line_pattern, line)
					if mo:
						amount = (float(mo.group(1)) / 100.)
						comment = mo.group(2).strip()
						GObject.idle_add(self._update_info_bar, amount, comment)

			process.poll()
		# Kill the subprocess if 
		if self._is_action_canceled:
			process.kill()
			retcode = 0
		else:
			retcode = process.returncode
			# Read the error output of AutoLaTeX
			for line in process.stderr:
				output = output + line
		process.stdout.close()
		process.stderr.close()
		
	    else:
		# Silent execution of the task
	        out, err = process.communicate()
	        retcode = process.returncode
	        output = err

	# If AutoLaTeX had failed, the output is assumed to
	# be the error message.
	# If AutoLaTeX had not failed, the output may contains
	# "warning" notifications.
	latex_warnings = []
	if retcode == 0:
		regex_expr = re.compile("^LaTeX Warning:\\s*(.*?)\\s*$")
		for output_line in re.split("[\n\r]+", output):
			mo = re.match(regex_expr, output_line)
			if mo:
				latex_warnings.append(mo.group(1))
		output = '' # Output is no more interesting

	# Remove the info bar from the inside of the Gtk thread
	GObject.idle_add(self._hide_info_bar)
	# Update the rest of the UI from the inside of the Gtk thread
	GObject.idle_add(self._caller._update_action_validity, True, output, latex_warnings)

    def _add_info_bar(self):
	gedit_tab = self._caller.window.get_active_tab()
	self._info_bar = Gedit.ProgressInfoBar()
	self._info_bar.set_stock_image(Gtk.STOCK_EXECUTE)
	self._info_bar.set_text(self._info_bar_label)
	self._sig_info_bar = self._info_bar.connect("response",
				self._on_cancel_action);
	self._info_bar.show()
	gedit_tab.set_info_bar(self._info_bar)

    def _hide_info_bar(self):
	if self._info_bar:
		self._info_bar.disconnect(self._sig_info_bar);
		self._info_bar.destroy()
		self._info_bar = None

    def _update_info_bar(self, progressValue, comment):
	if self._info_bar:
		self._info_bar.set_fraction(progressValue)
		if comment:
			self._info_bar.set_text(comment)

    def _on_cancel_action(self, widget, response, data=None):
	if response == Gtk.ResponseType.CANCEL:
		self._is_action_canceled = True
		if self._info_bar:
			self._info_bar.set_response_sensitive(
				Gtk.ResponseType.CANCEL,
				False)

#---------------------------------
# CLASS AutoLaTeXPlugin
#---------------------------------

# Plugin for Gedit
class AutoLaTeXPlugin(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):
    __gtype_name__ = "AutoLaTeXPlugin"
    window = GObject.property(type=Gedit.Window)
    
    #Constructor
    def __init__(self):
        GObject.Object.__init__(self)
	self._status_bar_context_id = None
	self._compilation_under_progress = False # Indicate if the compilation is under progress
	self._console_icon = None # Icon of the error console
	self._error_console = None # Current instance of the error console
	self._gsettings = gsettings.Manager()
	self._syntex_regex = re.compile('\%.*mainfile:\s*(.*)$')

    # Invoked when the configuration window is open
    def do_create_configure_widget(self):
        return plugin_config.Panel(self._gsettings, self.window)

    # Invoked when the plugin is activated 
    def do_activate(self):
	self._console_icon = self._get_icon('console')
	if not self._gsettings:
		self._gsettings = gsettings.Manager()
        self._add_ui()
	self._status_bar_context_id = self.window.get_statusbar().get_context_id("gedit-autolatex-plugin")
	self._check_autolatex_binaries()

    # Invoke when the plugin is desactivated
    def do_deactivate(self):
        self._remove_ui()
	self._gsettings.unbind()
	self._gsettings = None
	self._status_bar_context_id = None

    # Check if the AutoLaTeX binaries were found
    def _check_autolatex_binaries(self):
	if not utils.AUTOLATEX_BINARY and not utils.AUTOLATEX_BACKEND_BINARY:
		dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, _T("The programs 'autolatex' and 'autolatex-backend'\nwere not found.\nPlease fix the configuration of the AutoLaTeX plugin."))
		answer = dialog.run()
		dialog.destroy()
	elif not utils.AUTOLATEX_BINARY:
		dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, _T("The program 'autolatex' was not found.\nPlease fix the configuration of the AutoLaTeX plugin."))
		answer = dialog.run()
		dialog.destroy()
	elif not utils.AUTOLATEX_BACKEND_BINARY:
		dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, _T("The program 'autolatex-backend' was not found.\nPlease fix the configuration of the AutoLaTeX plugin."))
		answer = dialog.run()
		dialog.destroy()

    # Invoke when the UI is updated
    def do_update_state(self):
	directory = self._find_AutoLaTeX_dir()
	hasTeXDocument = self._is_TeX_document()
	hasAutoLaTeXDocument = (directory is not None)
	isInTeXContext = (hasTeXDocument or hasAutoLaTeXDocument)
	# Display or hide the menus
	self._menu.set_visible(isInTeXContext)
	self._document_actions.set_visible(isInTeXContext)
	self._texsensitive_actions.set_visible(isInTeXContext)
	self._general_actions.set_visible(isInTeXContext)
	# Test if the current document is inside a TeX context.
	if isInTeXContext:
		if directory:
			cfgFile = utils.get_autolatex_document_config_file(directory)
			hasDocConfFile = os.path.exists(cfgFile)
		else:
			hasDocConfFile = False
		hasUserConfFile = os.path.exists(utils.get_autolatex_user_config_file())
		# Change the sensitivity
		if self._document_actions:
		    self._document_actions.set_sensitive(hasAutoLaTeXDocument
				and not self._compilation_under_progress)
		if self._texsensitive_actions:
		    self._texsensitive_actions.set_sensitive(hasTeXDocument
				and not self._compilation_under_progress)
		if self._docconfsensitive_actions:
		    self._docconfsensitive_actions.set_sensitive(hasDocConfFile
				and not self._compilation_under_progress)
		if self._userconfsensitive_actions:
		    self._userconfsensitive_actions.set_sensitive(hasUserConfFile
				and not self._compilation_under_progress)
		
    # Update the UI according to the flag "compilation under progress"
    # and to compilation outputs
    def _update_action_validity(self, valid, console_content, latex_warnings):
	# Display or hide the error console if an error message is given or not
	if (console_content):
		if (not self._error_console or self._error_console.get_parent is None):
			if (not self._error_console):
				self._error_console = error_console.ErrorConsole(self.window)
			panel = self.window.get_bottom_panel()
			panel.add_item(self._error_console,
				"autolatex-console-panel",
				_T("AutoLaTeX Console"),
				Gtk.Image.new_from_pixbuf(self._console_icon))
		self._error_console.set_log(console_content, self._find_AutoLaTeX_dir())
	        panel.activate_item(self._error_console)
		if panel.get_property("visible") == False:
                        panel.set_property("visible", True)
	else:
		if (self._error_console):
			panel = self.window.get_bottom_panel()
			panel.remove_item(self._error_console)
			self._error_console = None
	# Update the status bar
	status_bar = self.window.get_statusbar()
	status_bar.remove_all(self._status_bar_context_id)
	if latex_warnings:
		message = latex_warnings[0]
		if len(latex_warnings)>1:
			message = "LaTeX: "+ message + "[...]"
		status_bar.push(self._status_bar_context_id, message)
	# Update the sensitivities of the Widgets
	self._compilation_under_progress = not valid
	self.do_update_state()    

    # Load an icon from the AutoLaTeX package
    def _get_icon(self, icon):
	return GdkPixbuf.Pixbuf.new_from_file(utils.make_toolbar_icon_path('autolatex-'+icon+'.png'))


    # Add any contribution to the Gtk UI
    def _add_ui(self):
	# Get the UI manager
        manager = self.window.get_ui_manager()
	# Create the Top menu for AutoLaTeX
        self._menu = Gtk.ActionGroup("AutoLaTeXMenu")
        self._menu.add_actions([
            ('AutoLaTeXMenu', None, _T("AutoLaTeX"), 
                None, _T("AutoLaTeX"), 
                None),
        ])
        manager.insert_action_group(self._menu)
	# Create the menu for SyncTeX
        self._synctex_menu = Gtk.ActionGroup("AutoLaTeXSyncTeXMenu")
        self._synctex_menu.add_actions([
            ('AutoLaTeXSyncTeXMenu', Gtk.STOCK_DISCONNECT, _T("SyncTeX"), 
                None, _T("SyncTeX"), 
                None),
        ])
	manager.insert_action_group(self._synctex_menu)
	# Create the group of actions that are needing an AutoLaTeX document
        self._document_actions = Gtk.ActionGroup("AutoLaTeXDocumentActions")
        self._document_actions.add_actions([
	    ('AutoLaTeXGenerateImageAction', None, _T("Generate images"), 
                None, _T("Generate the images with AutoLaTeX"), 
                self.on_generateimage_action_activate),
            ('AutoLaTeXCompileAction', None, _T("Compile"), 
                '<shift><ctrl>R', _T("Compile with AutoLaTeX"), 
                self.on_compile_action_activate),
            ('AutoLaTeXCleanAction', None, _T("Remove temporary files"), 
                None, _T("Clean with AutoLaTeX"), 
                self.on_clean_action_activate),
            ('AutoLaTeXCleanallAction', None, _T("Clean all"), 
                '<shift><ctrl>C', _T("Clean all with AutoLaTeX"), 
                self.on_cleanall_action_activate),
            ('AutoLaTeXViewAction', None, _T("View the PDF"), 
                None, _T("Open the PDF viewer"), 
                self.on_view_action_activate),
            ('AutoLaTeXMakeFlatAction', None, _T("Create flat version of the TeX document"), 
                None, _T("Create a flat version of the document, to be submitted to on-line publication systems (Elsevier...)"), 
                self.on_makeflat_action_activate),
        ])
        manager.insert_action_group(self._document_actions)
	# Create the group of actions that are needing an TeX document
        self._texsensitive_actions = Gtk.ActionGroup("AutoLaTeXTeXSensitiveActions")
        self._texsensitive_actions.add_actions([
            ('AutoLaTeXDocumentConfAction', None, _T("Document configuration"), 
                None, _T("Change the configuration for the document"), 
                self.on_document_configuration_action_activate),
        ])
        manager.insert_action_group(self._texsensitive_actions)
	# Create the group of actions that are needing the configuration file of a document
        self._docconfsensitive_actions = Gtk.ActionGroup("AutoLaTeXDocConfSensitiveActions")
        self._docconfsensitive_actions.add_actions([
            ('AutoLaTeXRemoveDocumentConfAction', None, _T("Delete document configuration"), 
                None, _T("Delete the configuration for the document"), 
                self.on_delete_document_configuration_action_activate),
        ])
        manager.insert_action_group(self._docconfsensitive_actions)
	# Create the group of actions that are needing the configuration file of the user
        self._userconfsensitive_actions = Gtk.ActionGroup("AutoLaTeXUserConfSensitiveActions")
        self._userconfsensitive_actions.add_actions([
            ('AutoLaTeXRemoveUserConfAction', None, _T("Delete user configuration"), 
                None, _T("Delete the configuration for the user"), 
                self.on_delete_user_configuration_action_activate),
        ])
        manager.insert_action_group(self._userconfsensitive_actions)
	# Create the group of actions that are not needing any special document
        self._general_actions = Gtk.ActionGroup("AutoLaTeXGeneralActions")
        self._general_actions.add_toggle_actions([
            ('AutoLaTeXEnableSyncTeXAction', None, _T("Force the use of SyncTeX"), 
                None, _T("Use SyncTeX even if the document and user configurations say 'no'"), 
                self.on_enable_synctex_action_activate),
	])
        self._general_actions.add_actions([
            ('AutoLaTeXUpdateForSyncTeXAction', None, _T("Update TeX file with SyncTeX reference"), 
                None, _T("Update the text of the TeX file to add the reference to the main document"), 
                self.on_update_for_synctex_action_activate),
            ('AutoLaTeXUserConfAction', None, _T("User configuration"), 
                None, _T("Change the configuration for the user"), 
                self.on_user_configuration_action_activate),
        ])
        manager.insert_action_group(self._general_actions)
	# Put the icons into the actions
	for definition in [	(self._document_actions, 'AutoLaTeXGenerateImageAction', 'images'),
				(self._document_actions, 'AutoLaTeXCompileAction', 'compile'),
				(self._document_actions, 'AutoLaTeXCleanAction', 'clean'),
				(self._document_actions, 'AutoLaTeXCleanallAction', 'cleanall'),
				(self._document_actions, 'AutoLaTeXViewAction', 'view'),
				(self._texsensitive_actions, 'AutoLaTeXDocumentConfAction', 'preferences'),
				(self._general_actions, 'AutoLaTeXUserConfAction', 'preferences')
			]:
		action = definition[0].get_action(definition[1])
		action.set_gicon(self._get_icon(definition[2]))
	# Add the Gtk contributions
	ui_path = os.path.join(utils.AUTOLATEX_PLUGIN_PATH, 'ui')
	self._ui_merge_ids = []
	for ui_file in [ 'menu.ui', 'toolbar.ui' ]:
	        self._ui_merge_ids.append(manager.add_ui_from_file(os.path.join(ui_path, ui_file)))
        manager.ensure_update()
	# Change the state of the check-boxes
	checkbox = self._general_actions.get_action('AutoLaTeXEnableSyncTeXAction')
	checkbox.set_active(self._gsettings.get_force_synctex())
	# Connect from gsettings
	self._gsettings.connect('force-synctex', self.on_gsettings_changed)

    # Remove all contributions to the Gtk UI
    def _remove_ui(self):
	# Disconnect from gsettings
	self._gsettings.disconnect('force-synctex')
	# Remove the error console
	if (self._error_console):
		panel = self.window.get_bottom_panel()
		panel.remove_item(self._error_console)
		self._error_console = None
	# Remove the Gtk Widgets
        manager = self.window.get_ui_manager()
	for merge_id in self._ui_merge_ids:
	        manager.remove_ui(merge_id)
        manager.remove_action_group(self._document_actions)
        manager.remove_action_group(self._texsensitive_actions)
        manager.remove_action_group(self._docconfsensitive_actions)
        manager.remove_action_group(self._userconfsensitive_actions)
        manager.remove_action_group(self._general_actions)
	manager.remove_action_group(self._synctex_menu)
        manager.remove_action_group(self._menu)
        manager.ensure_update()
    
    # Test if a given string is a standard extension for TeX document
    def _is_TeX_extension(self, ext):
	ext = ext.lower()
	if ext == '.tex' or ext =='.latex':
	    return True
	else:
	    return False

    # Replies if the active document is a TeX document
    def _is_TeX_document(self):
        doc = self.window.get_active_document()
        if doc:
            doc = Gedit.Document.get_location(doc)
	    if doc:
		ext = os.path.splitext(doc.get_path())[-1]
		return self._is_TeX_extension(ext)
        return False

    # Try to find the directory where an AutoLaTeX configuration file is
    # located. The search is traversing the parent directory from the current
    # document.
    def _find_AutoLaTeX_dir(self):
        adir = None
        doc = self.window.get_active_document()
        if doc:
            doc = Gedit.Document.get_location(doc)
	    if doc:
		document_name = doc.get_path()
                curdir = Gio.File.new_for_path(os.getcwd())
                doc = doc.get_parent()
		doc = curdir.resolve_relative_path(doc.get_path())
                doc = doc.get_path()
		document_dir = doc
                cfgFile = utils.get_autolatex_document_config_file(doc)
		previousFile = ''
	        while previousFile != cfgFile and not os.path.exists(cfgFile):
		    doc = os.path.dirname(doc)
		    previousFile = cfgFile
                    cfgFile = utils.get_autolatex_document_config_file(doc)

                if previousFile != cfgFile:
                    adir = os.path.dirname(cfgFile)
		else:
		    ext = os.path.splitext(document_name)[-1]
		    if self._is_TeX_extension(ext):
		        adir = document_dir

	return adir

    def _launch_AutoLaTeX(self, label, directive, params):
	directory = self._find_AutoLaTeX_dir()
	if directory:
	    GObject.idle_add(self._update_action_validity, False, None, None)
	    thread = _AutoLaTeXExecutionThread(self, label, self._gsettings, directory, directive, params)
	    thread.start()

    def _apply_general_autolatex_cli_options(self, params):
	if self._gsettings.get_force_synctex():
		params = [ '--synctex' ] + params
	params = [ utils.DEFAULT_LOG_LEVEL ] + params
	return params

    def on_clean_action_activate(self, action, data=None):
	self._launch_AutoLaTeX(
			_T("Removing the generated files (except the figures)"),
			'clean', self._apply_general_autolatex_cli_options(
			[ '--noview' ]))

    def on_cleanall_action_activate(self, action, data=None):
	self._launch_AutoLaTeX(
			_T("Removing the generated files and figures"),
			'cleanall', self._apply_general_autolatex_cli_options(
			[ '--noview' ]))

    def on_compile_action_activate(self, action, data=None):
	self._launch_AutoLaTeX(
			_T("Generating the document"),
			'all', self._apply_general_autolatex_cli_options(
			[ '--noview' ]))

    def on_generateimage_action_activate(self, action, data=None):
	self._launch_AutoLaTeX(
			_T("Generating the figures with the translators"),
			'images', self._apply_general_autolatex_cli_options(
			[ '--noview' ]))

    def on_view_action_activate(self, action, data=None):
	self._launch_AutoLaTeX(
			_T("Launching the viewer"),
			'view', self._apply_general_autolatex_cli_options(
			[ '--asyncview' ]))

    def on_document_configuration_action_activate(self, action, data=None):
	directory = self._find_AutoLaTeX_dir()
	if directory:
		cli_config.open_configuration_dialog(self.window, True, directory)

    def on_delete_document_configuration_action_activate(self, action, data=None):
	directory = self._find_AutoLaTeX_dir()
	if directory:
		cfgFile = utils.get_autolatex_document_config_file(directory)
		if os.path.exists(cfgFile):
			dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, _T("Do you want to delete the document configuration?"))
			answer = dialog.run()
			dialog.destroy()
			if answer == Gtk.ResponseType.YES:
				os.unlink(cfgFile)
				self.do_update_state()

    def on_user_configuration_action_activate(self, action, data=None):
	directory = self._find_AutoLaTeX_dir()
	if directory:
		cli_config.open_configuration_dialog(self.window, False, directory)

    def on_delete_user_configuration_action_activate(self, action, data=None):
	cfgFile = utils.get_autolatex_user_config_file()
	if os.path.exists(cfgFile):
		dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, _T("Do you want to delete the user configuration?"))
		answer = dialog.run()
		dialog.destroy()
		if answer == Gtk.ResponseType.YES:
			os.unlink(cfgFile)
			self.do_update_state()

    def on_enable_synctex_action_activate(self, action, data=None):
	checkbox = self._general_actions.get_action('AutoLaTeXEnableSyncTeXAction')
	self._gsettings.set_force_synctex(checkbox.get_active())

    def on_update_for_synctex_action_activate(self, action, data=None):
	if self._is_TeX_document():
		directory = self._find_AutoLaTeX_dir()
		view = self.window.get_active_view()
		text_buffer = view.get_buffer()
		found = None
		# Search in the first tree lines
		if text_buffer.get_line_count() > 0:
			found = self.__search_for_synctex_flag(text_buffer, 0)
		# Search in the last tree lines
		if not found and text_buffer.get_line_count() > 3:
			found = self.__search_for_synctex_flag(text_buffer,
					max(3,text_buffer.get_line_count()-3))
		# Add the SyncTeX flag
		if not found:
			private_config = utils.backend_get_configuration(
						directory,
						'all', '__private__');
			main_file = private_config.get('input', 'latex file', '');
			current_dir = Gio.File.new_for_path(os.getcwd())
			main_file = current_dir.resolve_relative_path(main_file).get_path()
        		current_document = self.window.get_active_document()
			document_file = Gedit.Document.get_location(current_document)
			if document_file:
				document_filename = current_dir.resolve_relative_path(document_file.get_path())
				document_filename = document_filename.get_path()
				if main_file != document_filename:
					document_dir = document_file.get_parent()
					rel_path = os.path.relpath(main_file, document_dir.get_path())
					text_buffer.insert_interactive(
						text_buffer.get_iter_at_line(0),
						unicode("% mainfile: "+rel_path+"\n"),
						-1,
						view.get_editable())

    def __search_for_synctex_flag(self, text_buffer, line_number):
	found = None
	i = 0
	text_iter1 = text_buffer.get_iter_at_line(line_number)
	while text_iter1 and i<3 and not found:
		text_iter2 = text_iter1.copy();
		text_iter2.forward_to_line_end()
		line = text_iter1.get_visible_text(text_iter2)
		mo = re.match(self._syntex_regex, line)
		if mo:
			found = mo.group(1)
		text_iter1 = text_iter2
		if not text_iter1.forward_line():
			i = 4
		else:
			i = i + 1
	return found

    def on_gsettings_changed(self, settings, key, data=None):
	if key == 'force-synctex':
		checkbox = self._general_actions.get_action('AutoLaTeXEnableSyncTeXAction')
		checkbox.set_active(self._gsettings.get_force_synctex())

    def on_enable_synctex_action_activate(self, action, data=None):
	checkbox = self._general_actions.get_action('AutoLaTeXEnableSyncTeXAction')
	self._gsettings.set_force_synctex(checkbox.get_active())

    def on_makeflat_action_activate(self, action, data=None):
	self._launch_AutoLaTeX(
			_T("Making the \"flat\" version of the document"),
			'makeflat', self._apply_general_autolatex_cli_options(
			[ '--noview' ]))

