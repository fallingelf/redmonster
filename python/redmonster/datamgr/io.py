# read_ndArch.py
#
# Code for reading ndArch files
#
# bolton@utah@iac 2014mayo
#

import numpy as n
from astropy.io import fits
from os import environ, makedirs, getcwd
from os.path import exists, join, basename
from astropy.io import fits
from time import gmtime, strftime
from glob import iglob

def read_ndArch(fname):
    """
    Read in an ndArch archetype file, parsing parameter baselines.
    (See ndArch data model document for file details.)
    
    Written by A. Bolton, U. of Utah (at IAC), May 2014
    
    Returns the tuple:
    (data, baselines, infodict)
    
    where
        
    data is an array containing archetype templates with
    shape (N_0, N_1,...,N_(npar-1),N_wave)
    
    baselines is a list containing the parameter baseline
    vectors along each of the parameter axes as numpy arrays
        
    infodict is a dictionary with the following keys:
    'filename': archetype source filename (w/o path)
    'class': archetype class taken from filename
    'version': archetype version taken from filename
    'coeff0': log10 Angstroms of the zeroth wavelength pixel
    'coeff1': delta-log10-Angstrom gridding in wavelength
    'nwave': number of pixels in the wavelength dimension
    'fluxunit': unit of archetype fluxes, if specified in file
    'par_names': names of parameter axes, if specified in file
    'par_units': units of parameter axes, if specified in file
    'par_axistype': baseline specification for each axis, from:
       'regular' (regular numerical gridding)
       'irregular' (irregular numerical gridding)
       'labeled' (string-labeled physical parameter gridding)
       'named' (arbitrary string-named objects)
       'index' (one-based index: default if no other spec)
    """
    # Test file generated by test_ndArch.py:
    # fname = 'ndArch-TEST-v00.fits'
    # Parse class and version from the filename:
    fn_ROOT = fname[:fname.rfind('.fits')]
    fn_CLASS = fn_ROOT.split('-')[-2]
    fn_VERSION = fn_ROOT.split('-')[-1]
    # Get the data and header:
    data = fits.getdata(fname).copy()
    header = fits.getheader(fname)
    # Identify how many parameters:
    npars = len(data.shape) - 1
    emptyparlist = ['']
    # Initialize output info dictionary:
    infodict = {'filename': fname.split('/')[-1],
        'class': fn_CLASS,
        'version': fn_VERSION,
        'coeff0': header['CRVAL1'],
        'coeff1': header['CDELT1'],
        'nwave': header['NAXIS1'],
        'fluxunit': '',
        'par_names': ['']*npars,
        'par_units': ['']*npars,
        'par_axistype': ['index']*npars}
    if ('BUNIT' in header): infodict['fluxunit'] = header['BUNIT']
    # Initialize list of baselines with index defaults:
    baselines = [n.arange(this_size)+1 for this_size in data.shape[:-1]]
    # Loop over parameters and construct baselines:
    for ipar in xrange(npars):
        # Translate Python axis index integer to FITS axis index string:
        ax = str(npars + 1 - ipar)
        # Populate name & units for this axis, if available:
        if ('CNAME'+ax in header): infodict['par_names'][ipar] = header['CNAME'+ax]
        if ('CUNIT'+ax in header): infodict['par_units'][ipar] = header['CUNIT'+ax]
        # The axis condition tests -- maybe inefficient to always compute
        # all of these, but makes for nicer code:
        is_regular = ('CRPIX'+ax in header) and \
            ('CRVAL'+ax in header) and \
            ('CDELT'+ax in header)
        pv_base = ['PV'+ax+'_'+str(j+1) for j in xrange(data.shape[ipar])]
        pv_test = n.asarray([this_pv in header for this_pv in pv_base])
        is_irregular = pv_test.prod() > 0
        ps_base = ['PS'+ax+'_'+str(j+1) for j in xrange(data.shape[ipar])]
        ps_test = n.asarray([this_ps in header for this_ps in ps_base])
        is_labeled = ps_test.prod() > 0
        n_base = ['N'+ax+'_'+str(j+1) for j in xrange(data.shape[ipar])]
        n_test = n.asarray([this_n in header for this_n in n_base])
        is_named = n_test.prod() > 0
        if is_regular:
            baselines[ipar] = (n.arange(data.shape[ipar]) + 1 - header['CRPIX'+ax]) \
                * header['CDELT'+ax] + header['CRVAL'+ax]
            infodict['par_axistype'][ipar] = 'regular'
        elif is_irregular:
            baselines[ipar] = n.asarray([header[this_pv] for this_pv in pv_base])
            infodict['par_axistype'][ipar] = 'irregular'
        elif is_labeled:
            baselines[ipar] = n.asarray([header[this_ps] for this_ps in ps_base])
            infodict['par_axistype'][ipar] = 'labeled'
        elif is_named:
            baselines[ipar] = n.asarray([header[this_n] for this_n in n_base])
            infodict['par_axistype'][ipar] = 'named'
    return data, baselines, infodict

# write_ndArch.py
#
# Code for writing ndArch files
#
# bolton@utah@iac 2014mayo
#

def write_ndArch(data, baselines, infodict):
    """
    Write archetype spectrum grid data to and ndArch file.
    (See ndArch data model document for file details.)
    
    Written by A. Bolton, U. of Utah (at IAC), May 2014
    
    Arguments are as follows:
    
    data is an array containing archetype templates with
    shape (N_0, N_1,...,N_(npar-1),N_wave)
    
    baselines is a list containing the parameter baseline
    arrays along each of the parameter axes.
    
    infodict is a dictionary with the following REQUIRED keys:
    'filename': archetype output filename (WITH path, as needed!!);
       to conform, must be of the form ndArch-CLASS-VERSION.fits
    'coeff0': log10 Angstroms of the zeroth wavelength pixel
    'coeff1': delta-log10-Angstrom gridding in wavelength
    'par_axistype': baseline specification for each axis, from:
       'regular' (regular numerical gridding)
       'irregular' (irregular numerical gridding)
       'labeled' (string-labeled physical parameter gridding)
       'named' (arbitrary string-named objects)
       'index' (one-based index; default -- need not be explicit)

    infodict can also have the following OPTIONAL keywords:
    'fluxunit': unit of archetype fluxes (string)
    'par_names': names of parameter axes (array of strings)
    'par_units': units of parameter axes (array of strings)

    *Note* that the 'infodict' entries are all the same as in
    read_ndArch, EXCEPT for 'filename', which behaves slightly
    differently in that it is to include the path for write_ndArch,
    but strips the path for read_ndArch.
    """
    # Initialize the HDU:
    hdu = fits.PrimaryHDU(data)
    # Set the flux units, if they are provided:
    if ('fluxunit' in infodict): hdu.header.set('BUNIT', value=infodict['fluxunit'], comment='Data unit')
    # Work out the number of parameters:
    npars = len(data.shape) - 1
    # Set the keywords for the wavelength baseline:
    hdu.header.set('CNAME1', value='loglam', comment='Axis 1 name')
    hdu.header.set('CUNIT1', value='log10(Angstroms)', comment='Axis 1 unit')
    hdu.header.set('CRPIX1', value=1., comment='Axis 1 reference pixel')
    hdu.header.set('CRVAL1', value=infodict['coeff0'], comment='Axis 1 reference value')
    hdu.header.set('CDELT1', value=infodict['coeff1'], comment='Axis 1 increment')
    # Loop over parameters...
    # Reverse ordering is to get things in FITS header in natural order.
    for ipar in range(npars)[::-1]:
        # Translate Python axis index integer to FITS axis index string:
        ax = str(npars + 1 - ipar)
        # Populate name & units for this axis, if available:
        if ('par_names' in infodict): hdu.header.set('CNAME'+ax, value=infodict['par_names'][ipar],
                                                     comment='Axis ' + ax + ' name')
        if ('par_units' in infodict): hdu.header.set('CUNIT'+ax, value=infodict['par_units'][ipar],
                                                     comment='Axis ' + ax + ' unit')
        # Parse the various possibilities for the baselines:
        if (infodict['par_axistype'][ipar].strip() == 'regular'):
            hdu.header.set('CRPIX'+ax, value=1.0, comment='Axis '+ax+' reference pixel')
            hdu.header.set('CRVAL'+ax, value=baselines[ipar][0], comment='Axis '+ax+' reference value')
            hdu.header.set('CDELT'+ax, value=(baselines[ipar][1]-baselines[ipar][0]), comment='Axis '+ax+' increment')
        elif (infodict['par_axistype'][ipar].strip() == 'irregular'):
            pv_base = ['PV'+ax+'_'+str(j+1) for j in xrange(data.shape[ipar])]
            for j in xrange(data.shape[ipar]): hdu.header.set(pv_base[j], value=baselines[ipar][j],
                                                              comment='Axis '+ax+' value at pixel ' + str(j+1))
        elif (infodict['par_axistype'][ipar].strip() == 'labeled'):
            ps_base = ['PS'+ax+'_'+str(j+1) for j in xrange(data.shape[ipar])]
            for j in xrange(data.shape[ipar]): hdu.header.set(ps_base[j], value=baselines[ipar][j],
                                                              comment='Axis '+ax+' label at pixel ' + str(j+1))
        elif (infodict['par_axistype'][ipar].strip() == 'named'):
            n_base = ['N'+ax+'_'+str(j+1) for j in xrange(data.shape[ipar])]
            for j in xrange(data.shape[ipar]): hdu.header.set(n_base[j], value=baselines[ipar][j],
                                                              comment='Axis '+ax+' name at pixel ' + str(j+1))
        else:
            pass
    hdu.writeto(infodict['filename'], clobber=True)


# Write output files after running entirety of redmonster
#
# Tim Hutchinson, University of Utah, August 2014
# t.hutchinson@utah.edu

class Write_Redmonster:
    '''
    Class to write output file at the end of running redmonster.  
    
    The zpick argument is simply the entire object created by running
    redmonster.physics.zpicker.py . The self.dest argument is a string
    containing the path in which to save the output file.
    
    If no dest argument is given, or the path does not exist, then the write_rm() method
    will default to writing in $REDMONSTER_SPECTRO_REDUX/$RUN2D/pppp/$RUN1D/ .  If the
    necessary environmental variables are also not specified, it will write in
    directory in which it is being run.

    The default behavior is to not clobber any older version of the output file in the
    given directory.  Setting clobber=True will overwrite old versions of the output file.
    '''
    def __init__(self, zpick, dest=None, clobber=False):
        self.clobber = clobber
        self.zpick = zpick
        #if dest and exists(dest): self.dest = dest
        if dest is not None:
            if exists(dest):
                self.dest = dest
            else:
                try:
                    makedirs(dest)
                    self.dest = dest
                except:
                    self.dest = None
        else:
            bsr = environ['REDMONSTER_SPECTRO_REDUX']
            run2d = environ['RUN2D']
            run1d = environ['RUN1D']
            if bsr and run2d and run1d:
                testpath = join(bsr, run2d, '%s' % zpick.plate, run1d)
                if exists(testpath):
                    self.dest = testpath
                else:
                    try:
                        makedirs(testpath)
                        self.dest = testpath
                    except:
                        self.dest = None
            else: self.dest = None

    def create_hdulist(self):
        # Get old header, append new stuff
        hdr = self.zpick.hdr
        hdr.extend([('VERS_RM','v0.-1','Version of redmonster used'),('DATE_RM',strftime("%Y-%m-%d_%H:%M:%S", gmtime()),'Time of redmonster completion'), ('NFIBERS', self.zpick.z.shape[0], 'Number of fibers')])
        prihdu = fits.PrimaryHDU(header=self.zpick.hdr)
        # Columns for 1st BIN table
        col1 = fits.Column(name='Z1', format='E', array=self.zpick.z[:,0])
        col2 = fits.Column(name='Z2', format='E', array=self.zpick.z[:,1])
        col3 = fits.Column(name='Z_ERR1', format='E', array=self.zpick.z_err[:,0])
        col4 = fits.Column(name='Z_ERR2', format='E', array=self.zpick.z_err[:,1])
        classx = n.array(map(repr,self.zpick.type))
        maxlen = max(map(len,classx))
        col5 = fits.Column(name='CLASS', format='%iA'%maxlen, array=self.zpick.type)
        # Change dictionary values of subclass to strings to be written into fits file.  eval('dictstring') will turn them back into dictionaries later.
        subclass = n.array(map(repr,self.zpick.subtype))
        maxlen = max(map(len,subclass))
        col6 = fits.Column(name='SUBCLASS', format='%iA'%maxlen, array=subclass)
        col7 = fits.Column(name='FIBERID', format='J', array=self.zpick.fiberid)
        minvec = n.array(map(repr,self.zpick.minvector)) # Change tuples of minvector to strings to be written into fits file.  eval('minvector') will turn them back into tuples later.
        maxlen = max(map(len,subclass))
        col8 = fits.Column(name='MINVECTOR', format='%iA'%maxlen, array=minvec)
        col9 = fits.Column(name='ZWARNING', format='E', array=self.zpick.zwarning)
        col10 = fits.Column(name='DOF', format='E', array=self.zpick.dof)
        col11 = fits.Column(name='NPOLY', format='E', array=self.zpick.npoly)
        fname = n.array(map(repr,self.zpick.fname))
        maxlen = max(map(len,fname))
        col12 = fits.Column(name='FNAME', format='%iA'%maxlen, array=fname)
        col13 = fits.Column(name='NPIXSTEP', format='E', array=self.zpick.npixstep)
        cols = fits.ColDefs([col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12, col13])
        tbhdu = fits.BinTableHDU.from_columns(cols) #tbhdu = fits.new_table(cols)
        # ImageHDU of models
        sechdu = fits.ImageHDU(data=self.zpick.models)
        self.thdulist = fits.HDUList([prihdu, tbhdu, sechdu]) #self.thdulist = fits.HDUList([prihdu, tbhdu])
    

    def write_fiberid(self):
        self.create_hdulist()

        if self.clobber:
            if self.dest is not None:
                self.thdulist.writeto(join(self.dest, '%s' % 'redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0])), clobber=self.clobber)
                print 'Writing redmonster file to %s' % join(self.dest, '%s' % 'redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0]))
            else:
                self.thdulist.writeto('redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0]), clobber=self.clobber)
                print 'Writing redmonster file to %s' % join( getcwd(), 'redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd) )
        else:
            if self.dest is not None:
                if exists(join(self.dest, '%s' % 'redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0]))):
                    self.thdulist.writeto(join(self.dest, '%s' % 'redmonster-%s-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0], strftime("%Y-%m-%d_%H:%M:%S", gmtime()))))
                    print 'Writing redmonster file to %s' % join(self.dest, '%s' % 'redmonster-%s-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0], strftime("%Y-%m-%d_%H:%M:%S", gmtime())))
                else:
                    self.thdulist.writeto(join(self.dest, '%s' % 'redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0])))
                    print 'Writing redmonster file to %s' % join(self.dest, '%s' % 'redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0]))
            else:
                if exists('redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0])):
                    self.thdulist.writeto('redmonster-%s-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0], strftime("%Y-%m-%d_%H:%M:%S", gmtime())))
                    print 'Writing redmonster file to %s' % join( getcwd(), 'redmonster-%s-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0], strftime("%Y-%m-%d_%H:%M:%S", gmtime())))
                else:
                    self.thdulist.writeto('redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0]))
                    print 'Writing redmonster file to %s' % join( getcwd(), 'redmonster-%s-%s-%03d.fits' % (self.zpick.plate, self.zpick.mjd, self.zpick.fiberid[0]))



    def write_plate(self):
        self.create_hdulist()
        
        if self.clobber:
            if self.dest is not None:
                self.thdulist.writeto(join(self.dest, '%s' % 'redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd)), clobber=self.clobber)
                print 'Writing redmonster file to %s' % join(self.dest, '%s' % 'redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd))
            else:
                self.thdulist.writeto('redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd), clobber=self.clobber)
                print 'Writing redmonster file to %s' % join( getcwd(), 'redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd) )
        else:
            if self.dest is not None:
                if exists(join(self.dest, '%s' % 'redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd))):
                    self.thdulist.writeto(join(self.dest, '%s' % 'redmonster-%s-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd, strftime("%Y-%m-%d_%H:%M:%S", gmtime()))))
                    print 'Writing redmonster file to %s' % join(self.dest, '%s' % 'redmonster-%s-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd, strftime("%Y-%m-%d_%H:%M:%S", gmtime())))
                else:
                    self.thdulist.writeto(join(self.dest, '%s' % 'redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd)))
                    print 'Writing redmonster file to %s' % join(self.dest, '%s' % 'redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd))
            else:
                if exists('redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd)):
                    self.thdulist.writeto('redmonster-%s-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd, strftime("%Y-%m-%d_%H:%M:%S", gmtime())))
                    print 'Writing redmonster file to %s' % join( getcwd(), 'redmonster-%s-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd, strftime("%Y-%m-%d_%H:%M:%S", gmtime())))
                else:
                    self.thdulist.writeto('redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd))
                    print 'Writing redmonster file to %s' % join( getcwd(), 'redmonster-%s-%s.fits' % (self.zpick.plate, self.zpick.mjd))


# Combine individual fiber fits files into a single plate file, or combine all plate files into an spAll-like file
# To combine fiber files, create object for a given plate, mjd and call method combine_fibers()
# To create spAll-like file, instantiate with no plate, mjd and call methond combine_plates()
#
# Tim Hutchinson, University of Utah, November 2014
# t.hutchinson@utah.edu

class Combine_Redmonster:

    def __init__(self, plate=None, mjd=None):
        self.plate = plate
        self.mjd = mjd


    def combine_fibers(self):
        self.filepaths = []
        self.type = []
        self.subtype = []
        self.fiberid = []
        self.minvec = []
        self.zwarning = []
        self.dof = []
        self.npoly = []
        self.fname = []
        self.npixstep = []
        self.models = None

        try: topdir = environ['REDMONSTER_SPECTRO_REDUX']
        except: topdir = None
        try: run2d = environ['RUN2D']
        except: run2d = None
        try: run1d = environ['RUN1D']
        except: run1d = None
        fiberdir = join(topdir, run2d, '%s' % self.plate, run1d, 'redmonster-%s-%s-*.fits' % (self.plate, self.mjd)) if topdir and run2d and run1d else None

        if fiberdir:
            for path in iglob(fiberdir):
                self.filepaths.append(path)
                fiberfile = basename(path)
                self.fiberid.append( int(fiberfile[22:25]) )
            self.z = n.zeros( (len(self.fiberid),2) )
            self.z_err = n.zeros( self.z.shape )
            try: self.hdr = fits.open( join( environ['BOSS_SPECTRO_REDUX'], environ['RUN2D'], 'spPlate-%s-%s.fits' % (self.plate,self.mjd) ) )[0].header
            except: self.hdr = None
            npix = fits.open( join( environ['BOSS_SPECTRO_REDUX'], environ['RUN2D'], 'spPlate-%s-%s.fits' % (self.plate,self.mjd) ) )[0].data.shape[1]
            self.models = n.zeros( (self.z.shape[0],npix) )
            for i, path in enumerate(self.filepaths):
                hdu = fits.open(path)
                self.z[i,0] = hdu[1].data.Z1[0]
                self.z[i,1] = hdu[1].data.Z2[0]
                self.z_err[i,0] = hdu[1].data.Z_ERR1[0]
                self.z_err[i,1] = hdu[1].data.Z_ERR2[0]
                self.type.append(hdu[1].data.CLASS[0])
                self.subtype.append(hdu[1].data.SUBCLASS[0])
                self.minvec.append(hdu[1].data.MINVEC[0])
                self.zwarning.append(hdu[1].data.ZWARNING[0])
                self.dof.append(hdu[1].data.DOF[0])
                self.npoly.append(hdu[1].data.NPOLY[0])
                self.fname.append(hdu[1].data.FNAME[0])
                self.npixstep.append(hdu[1].data.NPIXSTEP[0])
                self.models[i] = hdu[2].data[0]

        output = Write_Redmonster(self)
        output.write_plate()


    def combine_plates(self):
        pass


































