# -*- coding: utf-8 -*- 

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

### Copyright (C) 2002-2005 Stephen Kennedy <stevek@gnome.org>
### Copyright (C) 2005 Aaron Bentley <aaron.bentley@utoronto.ca>
### Copyright (C) 2007 José Fonseca <j_r_fonseca@yahoo.co.uk>

### Redistribution and use in source and binary forms, with or without
### modification, are permitted provided that the following conditions
### are met:
### 
### 1. Redistributions of source code must retain the above copyright
###    notice, this list of conditions and the following disclaimer.
### 2. Redistributions in binary form must reproduce the above copyright
###    notice, this list of conditions and the following disclaimer in the
###    documentation and/or other materials provided with the distribution.

### THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
### IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
### OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
### IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
### INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
### NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
### DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
### THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
### (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
### THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import errno
import _vc

class Vc(_vc.Vc):

    CMD = "git"
    NAME = "Git"
    PATCH_STRIP_NUM = 1
    PATCH_INDEX_RE = "^diff --git a/(.*) b/.*$"

    def __init__(self, location):
        self._tree_cache = None
        while location != "/":
            if os.path.isdir( "%s/.git" % location):
                self.root = location
                return
            location = os.path.dirname(location)
        raise ValueError()

    def commit_command(self, message):
        return [self.CMD,"commit","-m",message]
    def diff_command(self):
        return [self.CMD,"diff","HEAD"]
    def update_command(self):
        return [self.CMD,"pull"]
    def add_command(self, binary=0):
        return [self.CMD,"add"]
    def remove_command(self, force=0):
        return [self.CMD,"rm"]
    def revert_command(self):
        return [self.CMD,"checkout"]
    def get_working_directory(self, workdir):
        return self.root

    def cache_inventory(self, rootdir):
        self._tree_cache = self.lookup_tree(rootdir)

    def uncache_inventory(self):
        self._tree_cache = None

    def lookup_tree(self, rootdir):
        while 1:
            try:
                proc = os.popen("cd %s && git status" % self.root)
                entries = proc.read().split("\n")[:-1]
                break
            except OSError, e:
                if e.errno != errno.EAGAIN:
                    raise
        statemap = {
            "unknown": _vc.STATE_NONE,
            "new file": _vc.STATE_NEW,
            "copied": _vc.STATE_NORMAL,
            "deleted": _vc.STATE_REMOVED,
            "modified": _vc.STATE_MODIFIED,
            "renamed": _vc.STATE_NORMAL,
            "typechange": _vc.STATE_NORMAL,
            "unmerged": _vc.STATE_CONFLICT }
        tree_state = {}
        for entry in entries:
            if not entry.startswith("#\t"):
              continue
            try:
              statekey, name = entry[2:].split(":", 2)
            except ValueError:
              continue
            path = os.path.join(self.root, name.strip())
            state = statemap.get(statekey.strip(), _vc.STATE_NONE)
            tree_state[path] = state
        return tree_state

    def get_tree(self, directory):
        if self._tree_cache is None:
            return self.lookup_tree(directory)
        else:
            return self._tree_cache
        
    def lookup_files(self, dirs, files):
        "files is array of (name, path). assume all files in same dir"
        if len(files):
            directory = os.path.dirname(files[0][1])
        elif len(dirs):
            directory = os.path.dirname(dirs[0][1])
        else:
            return [],[]
        tree = self.get_tree(directory)

        retfiles = []
        retdirs = []
        gitfiles = {}
        for path,state in tree.iteritems():
            mydir, name = os.path.split(path)
            if path.endswith('/'):
                mydir, name = os.path.split(mydir)
            if mydir != directory:
                continue
            rev, date, options, tag = "","","",""
            if path.endswith('/'):
                retdirs.append( _vc.Dir(path[:-1], name, state))
            else:
                retfiles.append( _vc.File(path, name, state, rev, tag, options) )
            gitfiles[name] = 1
        for f,path in files:
            if f not in gitfiles:
                #state = ignore_re.match(f) == None and _vc.STATE_NONE or _vc.STATE_IGNORED
                state = _vc.STATE_NORMAL
                retfiles.append( _vc.File(path, f, state, "") )
        for d,path in dirs:
            if d not in gitfiles:
                #state = ignore_re.match(f) == None and _vc.STATE_NONE or _vc.STATE_IGNORED
                state = _vc.STATE_NORMAL
                retdirs.append( _vc.Dir(path, d, state) )
        return retdirs, retfiles
