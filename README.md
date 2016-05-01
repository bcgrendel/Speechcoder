Speechcoder
===========

Speechcoder allows you to code via speech recognition using Dragon Naturally Speaking and NatLink.  Out of the box, it's designed to work as a Python Script plugin for Notepad++, though with a bit of work, one could point the macro file at another plugin/application of one's making.


Tested on Windows 7 64bit with Dragon Naturally Speaking version 12, Dragonfly 0.6.5, NatLink 4.1, and Notepad++ v6.1.8
Beware that the version of Dragon you obtain is very important as newer versions might not be supported by this version of NatLink (required: version 4.1), so research it first!


Pre-Installation
------------
You'll need:

Dragon Naturally Speaking (version 12 recommended if you don't know if natlink supports the latest version of dragon)
Natlink

http://sourceforge.net/projects/natlink/files/natlink/natlinktest4.1/

Dragonfly

https://code.google.com/p/dragonfly/

Python 2.7

https://www.python.org/downloads/release/python-2711/

Notepad++

http://notepad-plus-plus.org/

Python Script plugin for Notepad++ [1]
	
http://sourceforge.net/projects/npppythonscript/
	
lXml library for python 2.7 (use the linked unofficial binary or build it yourself, as dragonfly may run into problems locating the DLL for lxml when installed from the usual source [https://pypi.python.org/pypi/lxml/3.2.3])

http://www.lfd.uci.edu/~gohlke/pythonlibs/bnrm5n67/lxml-3.2.3.win32-py2.7.exe
From: http://www.lfd.uci.edu/~gohlke/pythonlibs/

jellyfish and fuzzy modules.
	
https://pypi.python.org/pypi/jellyfish/0.1.2
https://pypi.python.org/pypi/Fuzzy

PyWin32 libs

http://sourceforge.net/projects/pywin32/


[1] Notepad++ python script plugin may need its copy of python27.dll replaced with the %windir%/system32/python27.dll copy. Rename notepad++ dll copy before replacing it to be safe (e.g. rename it to "python27.dll\_old").
This can be checked by comparing the versions reported when running python from command line versus running the notepad++ python console.


Installation
------------

I recommend placing the speechcoder\_ext folder somewhere easy to find like your root directory ("C:\\").  Now go into the speechcoder\_ext folder and run the setup.bat file.  You can (and should) read it to find that it creates an environmental variable named "NPP\_DRAGON" with the value set to the current directory (NPP\_DRAGON tells the application where this "speechcoder\_ext" directory was placed on your system). The speech rule file "grammar.ini" is in the grammar folder. Note that in grammar/context/ you'll find the xml folder for each supported language. The xml files define how each speech rule is rendered for that language.  E.G. the "make\_function" rule renders differently for Python and PHP.

Now you should have setup and tested NatLink to make sure it's working with Dragon. Go to the MacroSystem directory (if NatLink was installed to root, it might be in "C:\\NatLink\\NatLink\\MacroSystem". If you have multiple partitions remember to replace the 'C' in that filepath with the letter of your primary partition). Place the notepad++.py script here.

With Python Script installed on Notepad++, it's time to move the contents (not the folder itself!) of "npp\_python\_plugin" into the python script folder. To get that folder location, open Notepad++, look at the top menu and go to "Plugins"-&gt;"Python Script" -&gt; "New Script" and then in the dialog window just right click inside on a file or on the background where files would otherwise be and click properties (copy the filepath from location, navigate to it, and go inside the scripts directory if you're not already inside it).  For me that looks like "C:\\Documents and Settings\\&lt;USER&gt;\\Application Data\\Notepad++\\plugins\\config\\PythonScript\\scripts".  Now place the CONTENTS of "npp\_python\_plugin" here, not the folder itself.

Now if everything miraculously went okay, when you run Notepad++, go to "Plugins" - "Python Script" - "Scripts" - "npp\_dragonfly" to run the plugin.  Now you can begin coding by voice!


Speech Rules
------------

These are stored in the grammar.ini file.  (in the speechcoder\_ext\\grammar\\ directory)

To sum it all up into one:

	rule_name = saythis <dictation_variable> {choice_one | choice_two} [option <value2>]

"saythis" is a literal, as in you literally say "saythis" to match this part of the rule.
&lt;dictation\_variable&gt; is open dictation, anything goes (until another expected token is encountered, e.g. the following choice). Enclosed in angle brackets.
Curly braces enclose choices which are literals separated by pipe symbols ('|'). One of the choices must be uttered to match.
squares braces enclose option content, in this case the literal "option" followed by the dictation object "value2".


Output of the rules are defined in the individual language XML files.

More documentation to come later.  For now, feel free to look at grammar.ini, and try out the rules that are there.
