# -*- coding: utf-8 -*-
#
# Extract media urls from Css file and download
# Author: Kirill Panshin <http://github.com/kipanshi>
# Date: 2012-01-11
# Python version: 2.6.7
# CSS version: 2.0
# Tested on: Ubuntu 11.10 64-bit

"""
If you have a css and it contain media that you want to embed to
your project, you need to download not only this css file, but
also all the assets that are noted in there.

This package automates this process.

Dependencies:

    Wget tool


POSIX system is preferable.

USAGE:

    To run tests, do:

        $ python css_extract.py

    Example of API usage:
    (asuming your home folder name is "user")

        >>> from css_extract import Extractor
        >>> ex = Extractor('http://python.org/styles/styles.css', '/home/user/python_styles_css')
        >>> ex.asset_urls
        ['../images/header-bg2.png',
         '../images/nav-off-bg.png',
         ...
         'styles.css']
    
        >>> ex.run()
    
    Css file and it's assets will be downloaded preserving tree structure:
    
         python_styles_css /
        ├── images
        │   ├── blank.gif
        │   ├── bullet.gif
        │   ├── button-on-bg.png
        │   ├── header-bg2.png
        │   ├── nav-off-bg.png
        │   └── nav-on-bg.png
        └── styles
            └── styles.css

TODO: option for downloading assets via urllib2
 """


import os
import subprocess
import errno
import tempfile
import urllib2


class Extractor(object):
    """
    Extractor class implements methods for extraction asset urls from Css file
    and downloading them into corresponding folders.
    """

    def __init__(self, source_url, dest_path):
        """
        Input:
                    ``source_url``  Url of the Css on remote sever that contain assets
                                    we will be downloading

                    ``dest_path``   DirectoryPath where downloaded css with assets
                                    will be stored
        """
        self.css_file_name = source_url.split('/')[-1]
        self.css_base_url = source_url.replace(self.css_file_name, '')
        self.css_file_path = '/'.join(self.css_base_url.rstrip('/').split('/')[3:])

        self.base_site_url = source_url.replace('/'.join((self.css_file_path, self.css_file_name)), '')

        self.dest_path = dest_path

        # Download contents of Css to temporary file
        self.temp_css_file = tempfile.TemporaryFile()
        self.temp_css_file.writelines(
            urllib2.urlopen(source_url).readlines()
        )
        # Set cursor to the begining of a file
        self.temp_css_file.seek(0)

        # Extract list of asset urls
        self.asset_urls = [line.replace("url(\'", 'url('
                         ).replace("\')", ')'
                         ).replace('url(\"', 'url('
                         ).replace('\")', ')'
                         ).split('(')[1].split(')')[0]
                      for line in self.temp_css_file.readlines()
                        if 'url(' in line]

        # Append source css file to asset_urls
        self.asset_urls.append(self.css_file_name)

    def get_asset_list(self):
        """
        Get list (generator) of prepared tuples containing assets url,
        destination path and asset filename for each asset.
        """
        # Reversed is used to put css file url to the top of the list
        return (self._parse_asset_url(url) for url in reversed(self.asset_urls))

    def _parse_asset_url(self, url):
        """ Parse given raw url and return full url. """
        base_url = self.css_base_url

        def _handle_upper_level(base_url, raw_url):
            """ Recursively handle upper directory levels in url. """
            url = raw_url[3:]
            base_url = base_url.replace('/%s' % base_url.split('/')[-2], '')
            if url.startswith('../'):
                _url, base_url = _handle_upper_level(url, base_url)
            return base_url, url

        base_url, url = _handle_upper_level(base_url, url) \
            if url.startswith('../') \
                else (base_url.replace('%s/' % self.css_file_path, ''),
                      '/'.join((self.css_file_path, url.lstrip('/'))))

        asset_filename = url.split('/')[-1]
        asset_path = os.path.join(self.dest_path, url.replace('/%s' % asset_filename, ''))

        return ('%s%s' % (base_url, url), asset_path, asset_filename)

    def run(self):
        """
        Dowload Css and all it's media assets to the destination directory.
        """
        # TODO: Implement solution using urllib2
        # Create destination directory
        try:
            cd_or_create(self.dest_path)
        except OSError, e:
            print e

        # Loop assets and perform downloading
        for asset_url, dest_path, file_name in self.get_asset_list():
            try:
                cd_or_create(dest_path)
                asset_file = open(os.path.join(dest_path, file_name), 'rb')
                asset_file.close()
            except OSError, e:
                print e
                continue
            except IOError:
                print run_command('wget %s' % asset_url)


#===========================================#
# Utils for running programs from the shell #
#===========================================#


def run_command(command):
    """
    Run a command on local machine and get its output.
    """

    # Start the process
    p = subprocess.Popen(command.split(' '),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    # Communicate
    o, e = p.communicate()

    if e:
        return e

    # Return the output of the command
    return o


def pwd():
    """ Get the current working directory. """
    return os.getcwd()


def cd(path):
    """ Change the working directory to `path_to`. """
    os.chdir(path)


def cd_or_create(path, mode=0777):
    """
    Same as ``cd()`` but create ``path`` if it doesn't exist.
    """
    # Check ``path`` is available, create if possible
    try:
        os.mkdir(path, mode)
        cd(path)
    except OSError, e:
        # Path exist, do nothing
        if e.errno == errno.EEXIST:
            cd(path)
        elif e.errno == errno.ENOENT:
            cd_or_create(path[:-len(path.split('/')[-1])])
        else:
            raise OSError('Unable to create %s folder. Error: %s' % (path, e))


# Self testing
if __name__ == '__main__':
    import sys

    is_test_successful = True
    test_url = 'http://python.org/styles/styles.css'
    test_path = 'test_css_extract'
    current_path = os.path.abspath(os.path.dirname(__file__))

    ex = Extractor(test_url, os.path.join(current_path, test_path))
    ex.run()

    for asset_url, dest_path, file_name in ex.get_asset_list():
        try:
            asset_file = open(os.path.join(dest_path, file_name), 'rb')
            asset_file.close()
            print '.',
        except IOError:
            print 'Test failure for asset %s: %s' % \
                (asset_url, '/'.join((dest_path, file_name)))
            is_test_result = False

    if is_test_successful:
        print 'Tests Passed.'
    else:
        print 'Tests Failed.'

    # Cleanup test files
    run_command('rm -r %s' % os.path.join(current_path, test_path))
