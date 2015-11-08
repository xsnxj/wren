#!/usr/bin/env python

import codecs
import glob
import fnmatch
import os
import shutil
import subprocess
import sys
import time
import re
from datetime import datetime

import markdown


# Match a "## " style header. We require a space after "#" to avoid
# accidentally matching "#include" in code samples.
MARKDOWN_HEADER = re.compile(r'#+ ')

# Clean up a header to be a valid URL.
FORMAT_ANCHOR = re.compile(r'\?|!|:|/|\*|`')

def load_template():
  global template
  with codecs.open("doc/site/template.html", encoding="utf-8") as f:
    template = f.read()


def load_core_template():
  global template_core
  with codecs.open("doc/site/template-core.html", encoding="utf-8") as f:
    template_core = f.read()


def ensure_dir(path):
  if not os.path.exists(path):
    os.mkdir(path)


def is_up_to_date(path, out_path):
  dest_mod = 0
  if os.path.exists(out_path):
    dest_mod = os.path.getmtime(out_path)

  # See if the templates have changed.
  source_mod = os.path.getmtime('doc/site/template.html')
  if source_mod > dest_mod:
    load_template()
    return False

  # See if the templates have changed.
  source_mod = os.path.getmtime('doc/site/template-core.html')
  if source_mod > dest_mod:
    load_core_template()
    return False

  # See if it's up to date.
  source_mod = os.path.getmtime(path)
  return source_mod < dest_mod


def format_file(path, skip_up_to_date):
  basename = os.path.basename(path)
  basename = basename.split('.')[0]

  in_path = os.path.join('doc/site', path)
  out_path = "build/docs/" + os.path.splitext(path)[0] + ".html"

  if skip_up_to_date and is_up_to_date(in_path, out_path):
    # It's up to date.
    return

  title = ""
  category = ""

  # Read the markdown file and preprocess it.
  contents = ""
  with codecs.open(in_path, "r", encoding="utf-8") as input:
    # Read each line, preprocessing the special codes.
    for line in input:
      stripped = line.lstrip()
      indentation = line[:len(line) - len(stripped)]

      if stripped.startswith("^"):
        command,_,args = stripped.rstrip("\n").lstrip("^").partition(" ")
        args = args.strip()

        if command == "title":
          title = args
        elif command == "category":
          category = args
        else:
          print(' '.join(["UNKNOWN COMMAND:", command, args]))

      elif MARKDOWN_HEADER.match(stripped):
        # Add anchors to the headers.
        index = stripped.find(" ")
        headertype = stripped[:index]
        header = stripped[index:].strip()
        anchor = header.lower().replace(' ', '-')
        anchor = FORMAT_ANCHOR.sub('', anchor)

        contents += indentation + headertype
        contents += '{1} <a href="#{0}" name="{0}" class="header-anchor">#</a>\n'.format(anchor, header)

      else:
        # Forcibly add a space to the end of each line. Works around a bug in
        # the smartypants extension that removes some newlines that are needed.
        # https://github.com/waylan/Python-Markdown/issues/439
        if "//" not in line:
          contents = contents + line.rstrip() + ' \n'
        else:
          # Don't add a trailing space on comment lines since they may be
          # output lines which have a trailing ">" which makes the extra space
          # visible.
          contents += line

  html = markdown.markdown(contents, ['def_list', 'codehilite', 'smarty'])

  # Use special formatting for example output and errors.
  html = html.replace('<span class="c1">//&gt; ', '<span class="output">')
  html = html.replace('<span class="c1">//! ', '<span class="error">')

  modified = datetime.fromtimestamp(os.path.getmtime(in_path))
  mod_str = modified.strftime('%B %d, %Y')

  page_template = template
  if category == 'core':
    page_template = template_core

  fields = {
    'title': title,
    'html': html,
    'mod': mod_str,
    'category': category
  }

  # Write the html output.
  ensure_dir(os.path.dirname(out_path))

  with codecs.open(out_path, "w", encoding="utf-8") as out:
    out.write(page_template.format(**fields))

  print("converted " + path)


def check_sass():
    source_mod = os.path.getmtime('doc/site/style.scss')

    dest_mod = 0
    if os.path.exists('build/docs/style.css'):
      dest_mod = os.path.getmtime('build/docs/style.css')

    if source_mod < dest_mod:
        return

    subprocess.call(['sass', 'doc/site/style.scss', 'build/docs/style.css'])
    print("built css")


def format_files(skip_up_to_date):
  check_sass()

  for root, dirnames, filenames in os.walk('doc/site'):
    for filename in fnmatch.filter(filenames, '*.markdown'):
      f = os.path.relpath(os.path.join(root, filename), 'doc/site')
      format_file(f, skip_up_to_date)


# Clean the output directory.
if os.path.exists("build/docs"):
  shutil.rmtree("build/docs")
ensure_dir("build/docs")

load_template()
load_core_template()

# Process each markdown file.
format_files(False)

# Watch files.
if len(sys.argv) == 2 and sys.argv[1] == '--watch':
  while True:
    format_files(True)
    time.sleep(0.3)
