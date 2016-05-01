
Tested on Windows XP 32bit with Dragon Naturally Speaking version 12, Dragonfly 0.6.5, NatLink 4.1, and Notepad++ v6.1.8

Install notes for Dragon++ plugin:

You'll need:

Dragon Naturally Speaking (version 12 recommended if you don't know if natlink supports the latest version of dragon)
Natlink
	http://sourceforge.net/projects/natlink/files/natlink/natlinktest4.1/
Dragonfly
	https://code.google.com/p/dragonfly/
Python 2.7 (maybe google for the latest version to be sure. Version 2.7.5 is the latest as of this writing)
	http://www.python.org/download/releases/2.7.5/
Notepad++
	http://notepad-plus-plus.org/
Python Script plugin for Notepad++ [1]
	http://sourceforge.net/projects/npppythonscript/
lXml library for python 2.7 (use the linked unofficial binary or build it yourself, as dragonfly may run into problems locating the DLL for lxml when installed from the usual source [https://pypi.python.org/pypi/lxml/3.2.3])
	http://www.lfd.uci.edu/~gohlke/pythonlibs/bnrm5n67/lxml-3.2.3.win32-py2.7.exe
	From: http://www.lfd.uci.edu/~gohlke/pythonlibs/

[1] Notepad++ python script plugin may need its copy of python27.dll replaced with the %windir%/system32/python27.dll copy. Rename notepad++ dll copy before replacing it to be safe (e.g. rename it to "python27.dll_old").
This can be checked by comparing the versions reported when running python from command line versus running the notepad++ python console.

todo: Possible inclusions for fuzzy and jellyfish modules.  Awaiting implementation to know more.

https://pypi.python.org/pypi/Fuzzy
https://pypi.python.org/pypi/jellyfish/0.1.2
