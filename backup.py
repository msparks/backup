#!/usr/bin/python
# Copyright (c) 2009, Matt Sparks
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY MATT SPARKS ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL MATT SPARKS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import datetime
import getopt
import os
import sys
import yaml


class Profile(object):
  def __init__(self, profile_dict):
    self.name = profile_dict["name"]
    self._src = profile_dict["src"]
    self._dest = profile_dict["dest"]
    self._files = profile_dict.get("files", [])

  def sources(self):
    targets = []
    if self._src.startswith("/"):
      # local
      for filename in self._files:
        targets.append(_file_quote(os.path.join(self._src, filename)))
      return targets
    else:
      # remote (ssh)
      for filename in self._files:
        targets.append(filename)
      if not targets:
        return ["%s:" % profile._src]
      elif len(targets) == 1:
        return ["%s:%s" % (self._src, _file_escape(targets[0]))]
      else:
        return ["%s:\{%s\}" % (self._src, ",".join(_file_quote_list(targets)))]

  def target_path(self):
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    return os.path.join(self._dest, date_str)

  def latest_path(self):
    return os.path.join(self._dest, "latest")


def _file_quote(filename):
  return "'%s'" % filename.replace("'", "\\'")


def _file_quote_list(filenames):
  return [_file_quote(x) for x in filenames]


def backup_profile(profile):
  print "Processing profile '%s'..." % profile.name

  link_dest = profile.latest_path()
  if os.path.exists(link_dest):
    print "  hard link destination: %s" % link_dest
  else:
    print "  no link found to last backup"
    link_dest = None

  sources = profile.sources()
  target_dir = profile.target_path()

  rsync_args = ["-aR", "--delete"]
  rsync_args.append("-v")  # verbose
  #rsync_args.append("-n")  # dry-run
  if link_dest:
    rsync_args.extend(["--link-dest", _file_quote(link_dest)])

  rsync_args.extend(sources)
  rsync_args.append(_file_quote(target_dir))

  print "  rsync arguments:"
  for arg in rsync_args:
    print "    %s" % arg

  ret_val = os.system("rsync %s" % " ".join(rsync_args))
  exit_code = ret_val >> 8
  print "  rsync exited with code: %d" % exit_code

  if exit_code == 0:
    # create 'latest' symlink
    if os.path.islink(profile.latest_path()):
      os.unlink(profile.latest_path())
    os.symlink(target_dir, profile.latest_path())
    print "  updated 'latest' symlink"

  print


def backup_profiles(profiles):
  for profile in profiles:
    backup_profile(profile)


def main():
  config_path = os.path.join(os.path.dirname(sys.argv[0]), "config.yaml")
  config_path = os.path.abspath(config_path)
  try:
    config_fh = open(config_path, "r")
  except IOError:
    print >>sys.stderr, "Failed to open config file '%s'." % config_path
    sys.exit(1)

  opts, profile_names = getopt.getopt(sys.argv[1:], "p")
  profiles = []

  config = yaml.load_all(config_fh)
  for record in config:
    if "name" not in record or "src" not in record or "dest" not in record:
      print >>std.stderr, "Warning: config item missing name, src, or dest."
      continue
    if record["name"] in profile_names or not profile_names:
      profiles.append(Profile(record))
  config_fh.close()

  backup_profiles(profiles)


if __name__ == "__main__":
  main()
