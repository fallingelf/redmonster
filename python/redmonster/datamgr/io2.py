# Write output files after running entirety of redmonster
#
# Tim Hutchinson, University of Utah, August 2014
#
# Edited to reflect changes made to zfitter and zpicker, July 2015
# t.hutchinson@utah.edu

import numpy as n
from astropy.io import fits
from os import environ, makedirs, getcwd, remove
from os.path import exists, join, basename
from astropy.io import fits
from time import gmtime, strftime
from glob import iglob
import re

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
    def __init__(self, zpick, dest=None, clobber=True):
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
        hdr.extend([('VERS_RM','v0.1.0','Version of redmonster used'),('DATE_RM',strftime("%Y-%m-%d_%H:%M:%S", gmtime()),'Time of redmonster completion'), ('NFIBERS', len(self.zpick.z), 'Number of fibers'), ('NZ', len(self.zpick.z[0]), 'Number of redshifts retained'),('RCHI2TH',self.zpick.threshold,'Reduced chi**2 threshold used')])
        prihdu = fits.PrimaryHDU(header=self.zpick.hdr)
        # Columns for 1st BIN table
        colslist = []
        colslist.append( fits.Column(name='FIBERID', format='J', array=self.zpick.fiberid) )
        colslist.append( fits.Column(name='DOF', format='J', array=self.zpick.dof) )
        if hasattr(self.zpick, 'boss_target1'):
            colslist.append( fits.Column(name='BOSS_TARGET1', format='J', array=self.zpick.boss_target1) )
        if hasattr(self.zpick, 'eboss_target1'):
            colslist.append( fits.Column(name='EBOSS_TARGET1', format='J', array=self.zpick.eboss_target1) )
        for i in xrange(len(self.zpick.z[0])):
            zlist = []
            zerrlist = []
            classlist = []
            subclasslist = []
            minvectorlist = []
            npolylist = []
            fnamelist = []
            npixsteplist = []
            minrchi2list = []
            fslist = []
            for j in xrange(len(self.zpick.z)):
                zlist.append( self.zpick.z[j][i] )
                zerrlist.append( self.zpick.z_err[j][i] )
                classlist.append( self.zpick.type[j][i] )
                subclasslist.append( repr(self.zpick.subtype[j][i]) )
                fnamelist.append( self.zpick.fname[j][i] )
                minvectorlist.append( repr(self.zpick.minvector[j][i]) )
                npolylist.append( self.zpick.npoly[j][i] )
                npixsteplist.append( self.zpick.npoly[j][i] )
                minrchi2list.append( self.zpick.minrchi2[j][i] )
                fslist.append( repr(self.zpick.fs[j][i]) )
            colslist.append( fits.Column(name='Z%s' % (i+1), format='E', array=zlist) )
            colslist.append( fits.Column(name='Z_ERR%s' % (i+1), format='E', array=zerrlist) )
            colslist.append( fits.Column(name='CLASS%s' % (i+1), format='%iA' % max(map(len,classlist)), array=classlist) )
            colslist.append( fits.Column(name='SUBCLASS%s' % (i+1), format='%iA' % max(map(len,subclasslist)), array=subclasslist) )
            colslist.append( fits.Column(name='FNAME%s' % (i+1), format='%iA' % max(map(len,fnamelist)), array=fnamelist) )
            colslist.append( fits.Column(name='MINVECTOR%s' % (i+1), format='%iA' % max(map(len,minvectorlist)), array=minvectorlist) )
            colslist.append( fits.Column(name='MINRCHI2%s' % (i+1), format='E', array=minrchi2list) )
            colslist.append( fits.Column(name='NPOLY%s' % (i+1), format='J', array=npolylist) )
            colslist.append( fits.Column(name='NPIXSTEP%s' % (i+1), format='J', array=npixsteplist) )
            colslist.append( fits.Column(name='THETA%s' % (i+1), format='%iA' % max(map(len,fslist)), array=fslist) )
        colslist.append( fits.Column(name='ZWARNING', format='J', array=self.zpick.zwarning) )
        colslist.append( fits.Column(name='RCHI2DIFF', format='E', array=self.zpick.rchi2diff) )
        cols = fits.ColDefs(colslist)
        tbhdu = fits.BinTableHDU.from_columns(cols) #tbhdu = fits.new_table(cols)
        # ImageHDU of models
        sechdu = fits.ImageHDU(data=self.zpick.models)
        self.thdulist = fits.HDUList([prihdu, tbhdu, sechdu]) #self.thdulist = fits.HDUList([prihdu, tbhdu])


    def write_fiber(self):
        self.clobber = True # Temporary fix!!
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
# To combine fiber files, create object for a given plate, mjd and call method merge_fibers()
# To create spAll-like file, instantiate with no plate, mjd and call methond merge_plates()
#
# Tim Hutchinson, University of Utah, November 2014
# t.hutchinson@utah.edu

class Merge_Redmonster:
    
    def __init__(self, plate=None, mjd=None, temp=None):
        self.plate = plate
        self.mjd = mjd
        self.temp = temp
    
    
    def merge_fibers(self):
        self.filepaths = []
        self.type = []
        self.subtype = []
        self.fiberid = []
        self.minvector = []
        self.minrchi2 = []
        self.zwarning = []
        self.dof = []
        self.npoly = []
        self.fname = []
        self.npixstep = []
        self.boss_target1 = []
        self.chi2diff = []
        self.models = None
        self.hdr = None
        
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
            self.z = n.zeros( (len(self.fiberid),5) )
            self.z_err = n.zeros( self.z.shape )
            try: self.hdr = fits.open( join( environ['BOSS_SPECTRO_REDUX'], environ['RUN2D'], '%s' % self.plate, 'spPlate-%s-%s.fits' % (self.plate,self.mjd) ) )[0].header
            except: self.hdr = fits.Header()
            npix = fits.open( join( environ['BOSS_SPECTRO_REDUX'], environ['RUN2D'], '%s' % self.plate, 'spPlate-%s-%s.fits' % (self.plate,self.mjd) ) )[0].data.shape[1]
            self.models = n.zeros( (self.z.shape[0],npix) )
            self.filepaths.sort()
            self.fiberid.sort()
            for i, path in enumerate(self.filepaths):
                hdu = fits.open(path)
                self.z[i,0] = hdu[1].data.Z1[0]
                self.z[i,1] = hdu[1].data.Z2[0]
                self.z_err[i,0] = hdu[1].data.Z_ERR1[0]
                self.z_err[i,1] = hdu[1].data.Z_ERR2[0]
                self.type.append(hdu[1].data.CLASS1[0])
                self.subtype.append(hdu[1].data.SUBCLASS1[0])
                self.minvector.append(hdu[1].data.MINVECTOR1[0])
                self.zwarning.append(hdu[1].data.ZWARNING[0])
                self.dof.append(hdu[1].data.DOF[0])
                self.npoly.append(hdu[1].data.NPOLY1[0])
                self.fname.append(hdu[1].data.FNAME1[0])
                self.npixstep.append(hdu[1].data.NPIXSTEP1[0])
                self.chi2diff.append(hdu[1].data.RCHI2DIFF[0])
                try:
                    self.boss_target1.append(hdu[1].data.BOSS_TARGET1[0])
                except:
                    pass
                try:
                    self.eboss_target1.append(hdu[1].data.EBOSS_TARGET1[0])
                except:
                    pass
                self.models[i] = hdu[2].data[0]
                #remove(path)
            output = Write_Redmonster(self, clobber=True)
            output.write_plate()


    def merge_plates(self):
        self.type = []
        self.subtype = []
        self.fiberid = []
        self.minvector = []
        self.zwarning = []
        self.dof = []
        self.npoly = []
        self.fname = []
        self.npixstep = []
        self.chi2diff = []
        self.boss_target1 = []
        self.eboss_target1 = []
        self.plates = []
        self.models = n.zeros((1,1))
        self.hdr = fits.Header()
        
        try: topdir = environ['REDMONSTER_SPECTRO_REDUX']
        except: topdir = None
        try: run2d = environ['RUN2D']
        except: run2d = None
        try: run1d = environ['RUN1D']
        except: run1d = None
        platedir = join( topdir, run2d, '*') if topdir and run2d else None
        
        if platedir:
            for path in iglob(platedir):
                self.plates.append( basename(path) )
            self.plates.sort()
            for listitem in self.plates:
                if listitem[-5:] == '.fits': self.plates.remove(listitem)
            self.fiberid = self.plates
            for plate in self.plates:
                print 'Merging plate %s' % plate
                mjds = []
                try:
                    for x in iglob( join( topdir, run2d, '%s' % plate, run1d, 'redmonster-%s-*.fits' % plate) ):
                        if basename(x)[16:21] not in mjds: mjds.append(basename(x)[16:21])
                #if mjds is not basename(x)[16:21]: mjds.append(basename(x)[16:21])
                #else: mjds.append( basename(x)[16:21] )
                except: mjds = None
                if mjds is not [] and mjds is not None:
                    for mjd in mjds:
                        filepath = join( topdir, run2d, str(plate), run1d, 'redmonster-%s-%s.fits' % (plate, mjd))
                        #npix = fits.open( join( environ['BOSS_SPECTRO_REDUX'], environ['RUN2D'], '%s' % plate, 'spPlate-%s-%s.fits' % (plate, mjd) ) )[0].data.shape[1]
                        if exists(filepath):
                            hdu = fits.open(filepath)
                            self.type += hdu[1].data.CLASS.tolist()
                            self.subtype += hdu[1].data.SUBCLASS.tolist()
                            self.minvector += hdu[1].data.MINVECTOR.tolist()
                            self.zwarning += hdu[1].data.ZWARNING.tolist()
                            self.dof += hdu[1].data.DOF.tolist()
                            self.npoly += hdu[1].data.NPOLY.tolist()
                            self.fname += hdu[1].data.FNAME.tolist()
                            self.npixstep += hdu[1].data.NPIXSTEP.tolist()
                            self.chi2diff += hdu[1].data.CHI2DIFF.tolist()
                            try: self.z1 = n.append(self.z1, hdu[1].data.Z1)
                            except: self.z1 = hdu[1].data.Z1
                            try: self.z_err1 = n.append(self.z_err1, hdu[1].data.Z_ERR1)
                            except: self.z_err1 = hdu[1].data.Z_ERR1
                            try: self.z2 = n.append(self.z2, hdu[1].data.Z2)
                            except: self.z2 = hdu[1].data.Z2
                            try: self.z_err2 = n.append(self.z_err2, hdu[1].data.Z_ERR2)
                            except: self.z_err2 = hdu[1].data.Z_ERR2
        self.z = n.zeros( (self.z1.shape[0],2) )
        self.z_err = n.zeros( self.z.shape )
        self.z[:,0] = self.z1
        self.z[:,1] = self.z2
        self.z_err[:,0] = self.z_err1
        self.z_err[:,1] = self.z_err2
        
        output = Write_Redmonster(self)
        output.create_hdulist()
        output.thdulist.writeto( join( topdir, run2d, 'redmonster-all-%s.fits' % run2d), clobber=True)


    def merge_fibers2(self):
        self.filepaths = []
        self.fiberid = []
        self.dof = []
        self.boss_target1 = []
        self.eboss_target1 = []
        self.z1 = []
        self.z_err1 = []
        self.class1 = []
        self.subclass1 = []
        self.fname1 = []
        self.minvector1 = []
        self.minrchi21 = []
        self.npoly1 = []
        self.npixstep1 = []
        self.theta1 = []
        self.z2 = []
        self.z_err2 = []
        self.class2 = []
        self.subclass2 = []
        self.fname2 = []
        self.minvector2 = []
        self.minrchi22 = []
        self.npoly2 = []
        self.npixstep2 = []
        self.theta2 = []
        self.z3 = []
        self.z_err3 = []
        self.class3 = []
        self.subclass3 = []
        self.fname3 = []
        self.minvector3 = []
        self.minrchi23 = []
        self.npoly3 = []
        self.npixstep3 = []
        self.theta3 = []
        self.z4 = []
        self.z_err4 = []
        self.class4 = []
        self.subclass4 = []
        self.fname4 = []
        self.minvector4 = []
        self.minrchi24 = []
        self.npoly4 = []
        self.npixstep4 = []
        self.theta4 = []
        self.z5 = []
        self.z_err5 = []
        self.class5 = []
        self.subclass5 = []
        self.fname5 = []
        self.minvector5 = []
        self.minrchi25 = []
        self.npoly5 = []
        self.npixstep5 = []
        self.theta5 = []
        self.zwarning = []
        self.rchi2diff = []
    
        try: topdir = environ['REDMONSTER_SPECTRO_REDUX']
        except: topdir = None
        try: run2d = environ['RUN2D']
        except: run2d = None
        try: run1d = environ['RUN1D']
        except: run1d = None
        fiberdir = join(topdir, run2d, '%s' % self.plate, run1d, 'redmonster-%s-%s-*.fits' % (self.plate, self.mjd)) if topdir and run2d and run1d else None
        
        if fiberdir:
            for path in iglob(fiberdir):
                self.filepaths.append( path )
                fiberfile = basename( path )
                self.fiberid.append( int(fiberfile[22:25]) )
            try:
                self.hdr = fits.open( join( environ['BOSS_SPECTRO_REDUX'], environ['RUN2D'], '%s' % self.plate, 'spPlate-%s-%s.fits' % (self.plate,self.mjd) ) )[0].header
            except:
                self.hdr = fits.Header()
            npix = fits.open( join( environ['BOSS_SPECTRO_REDUX'], environ['RUN2D'], '%s' % self.plate, 'spPlate-%s-%s.fits' % (self.plate,self.mjd) ) )[0].data.shape[1]
            self.models = n.zeros( (len(self.fiberid),5,npix) )
            self.filepaths.sort()
            self.fiberid.sort()
            haveHeader = False
            for i, path in enumerate(self.filepaths):
                hdu = fits.open(path)
                if not haveHeader:
                    self.hdr = self.zpick.hdr
                    haveHeader = True
                self.dof.append(hdu[1].data.DOF[0])
                self.z1.append(hdu[1].data.Z1[0])
                self.z_err1.append(hdu[1].data.Z_ERR1[0])
                self.class1.append(hdu[1].data.CLASS1[0])
                self.subclass1.append(SUBCLASS1[0])
                self.fname1.append(hdu[1].data.FNAME1[0])
                self.minvector1.append(hdu[1].data.MINVECTOR1[0])
                self.minrchi21.append(hdu[1].data.MINRCHI21[0])
                self.npoly1.append(hdu[1].data.NPOLY1[0])
                self.npixstep1.append(hdu[1].data.NPIXSTEP1[0])
                self.theta1.append(hdu[1].data.THETA1[0])
                self.z2.append(hdu[1].data.Z2[0])
                self.z_err2.append(hdu[1].data.Z_ERR2[0])
                self.class2.append(hdu[1].data.CLASS2[0])
                self.subclass2.append(hdu[1].data.SUBCLASS2[0])
                self.fname2.append(hdu[1].data.FNAME2[0])
                self.minvector2.append(hdu[1].data.MINVECTOR2[0])
                self.minrchi22.append(hdu[1].data.MINRCHI22[0])
                self.npoly2.append(hdu[1].data.NPOLY2[0])
                self.npixstep2.append(hdu[1].data.NPIXSTEP2[0])
                self.theta2.append(hdu[1].data.THETA2[0])
                self.z3.append(hdu[1].data.Z3[0])
                self.z_err3.append(hdu[1].data.Z_ERR3[0])
                self.class3.append(hdu[1].data.CLASS3[0])
                self.subclass3.append(hdu[1].data.SUBCLASS3[0])
                self.fname3.append(hdu[1].data.FNAME3[0])
                self.minvector3.append(hdu[1].data.MINVECTOR3[0])
                self.minrchi23.append(hdu[1].data.MINRCHI23[0])
                self.npoly3.append(hdu[1].data.NPOLY3[0])
                self.npixstep3.append(hdu[1].data.NPIXSTEP3[0])
                self.theta3.append(hdu[1].data.THETA3[0])
                self.z4.append(hdu[1].data.Z4[0])
                self.z_err4.append(hdu[1].data.Z_ERR4[0])
                self.class4.append(hdu[1].data.CLASS4[0])
                self.subclass4.append(hdu[1].data.SUBCLASS4[0])
                self.fname4.append(hdu[1].data.FNAME4[0])
                self.minvector4.append(hdu[1].data.MINVECTOR4[0])
                self.minrchi24.append(hdu[1].data.MINRCHI24[0])
                self.npoly4.append(hdu[1].data.NPOLY4[0])
                self.npixstep4.append(hdu[1].data.NPIXSTEP4[0])
                self.theta4.append(hdu[1].data.THETA4[0])
                self.z5.append(hdu[1].data.Z5[0])
                self.z_err5.append(hdu[1].data.Z_ERR5[0])
                self.class5.append(hdu[1].data.CLASS5[0])
                self.subclass5.append(hdu[1].data.SUBCLASS5[0])
                self.fname5.append(hdu[1].data.FNAME5[0])
                self.minvector5.append(hdu[1].data.MINVECTOR5[0])
                self.minrchi25.append(hdu[1].data.MINRCHI25[0])
                self.npoly5.append(hdu[1].data.NPOLY5[0])
                self.npixstep5.append(hdu[1].data.NPIXSTEP5[0])
                self.theta5.append(hdu[1].data.THETA5[0])
                self.zwarning.append(hdu[1].data.ZWARNING[0])
                self.rchi2diff.append(hdu[1].data.RCHI2DIFF[0])
                try:
                    self.boss_target1.append(hdu[1].data.BOSS_TARGET1[0])
                except:
                    pass
                try:
                    self.eboss_target1.append(hdu[1].data.EBOSS_TARGET1[0])
                except:
                    pass
                self.models[i] = hdu[2].data[0]
            #remove(path)
            prihdu = fits.PrimaryHDU(header=self.hdr)
            colslist = []
            colslist.append( fits.Column(name='FIBERID', format='J', array=self.fiberid) )
            colslist.append( fits.Column(name='DOF', format='J', array=self.dof) )
            colslist.append( fits.Column(name='BOSS_TARGET1', format='J', array=self.boss_target1) )
            colslist.append( fits.Column(name='EBOSS_TARGET1', format='J', array=self.eboss_target1) )
            colslist.append( fits.Column(name='Z1', format='E', array=self.z1) )
            colslist.append( fits.Column(name='Z_ERR1', format='E', array=self.z_err1) )
            colslist.append( fits.Column(name='CLASS1', format='%iA' % max(map(len,self.class1)), array=self.class1) )
            colslist.append( fits.Column(name='SUBCLASS1', format='%iA' % max(map(len,self.subclass1)), array=self.subclass1) )
            colslist.append( fits.Column(name='FNAME1', format='%iA' % max(map(len,self.fname1)), array=self.fname1) )
            colslist.append( fits.Column(name='MINVECTOR1', format='%iA' % max(map(len,self.minvector1)), array=self.minvector1) )
            colslist.append( fits.Column(name='MINRCHI21', format='E', array=self.minrchi21) )
            colslist.append( fits.Column(name='NPOLY1', format='J', array=self.npoly1) )
            colslist.append( fits.Column(name='NPIXSTEP1', format='J', array=self.npixstep1) )
            colslist.append( fits.Column(name='THETA1', format='%iA' % max(map(len,self.theta1)), array=self.theta1) )
            colslist.append( fits.Column(name='Z2', format='E', array=self.z2) )
            colslist.append( fits.Column(name='Z_ERR2', format='E', array=self.z_err2) )
            colslist.append( fits.Column(name='CLASS2', format='%iA' % max(map(len,self.class2)), array=self.class1) )
            colslist.append( fits.Column(name='SUBCLASS2', format='%iA' % max(map(len,self.subclass2)), array=self.subclass1) )
            colslist.append( fits.Column(name='FNAME2', format='%iA' % max(map(len,self.fname2)), array=self.fname1) )
            colslist.append( fits.Column(name='MINVECTOR2', format='%iA' % max(map(len,self.minvector2)), array=self.minvector1) )
            colslist.append( fits.Column(name='MINRCHI22', format='E', array=self.minrchi22) )
            colslist.append( fits.Column(name='NPOLY2', format='J', array=self.npoly2) )
            colslist.append( fits.Column(name='NPIXSTEP2', format='J', array=self.npixstep2) )
            colslist.append( fits.Column(name='THETA2', format='%iA' % max(map(len,self.theta2)), array=self.theta1) )
            colslist.append( fits.Column(name='Z3', format='E', array=self.z3) )
            colslist.append( fits.Column(name='Z_ERR3', format='E', array=self.z_err3) )
            colslist.append( fits.Column(name='CLASS3', format='%iA' % max(map(len,self.class3)), array=self.class1) )
            colslist.append( fits.Column(name='SUBCLASS3', format='%iA' % max(map(len,self.subclass3)), array=self.subclass1) )
            colslist.append( fits.Column(name='FNAME3', format='%iA' % max(map(len,self.fname3)), array=self.fname1) )
            colslist.append( fits.Column(name='MINVECTOR3', format='%iA' % max(map(len,self.minvector3)), array=self.minvector1) )
            colslist.append( fits.Column(name='MINRCHI23', format='E', array=self.minrchi23) )
            colslist.append( fits.Column(name='NPOLY3', format='J', array=self.npoly3) )
            colslist.append( fits.Column(name='NPIXSTEP3', format='J', array=self.npixstep3) )
            colslist.append( fits.Column(name='THETA3', format='%iA' % max(map(len,self.theta3)), array=self.theta1) )
            colslist.append( fits.Column(name='Z4', format='E', array=self.z4) )
            colslist.append( fits.Column(name='Z_ERR4', format='E', array=self.z_err4) )
            colslist.append( fits.Column(name='CLASS4', format='%iA' % max(map(len,self.class4)), array=self.class1) )
            colslist.append( fits.Column(name='SUBCLASS4', format='%iA' % max(map(len,self.subclass4)), array=self.subclass1) )
            colslist.append( fits.Column(name='FNAME4', format='%iA' % max(map(len,self.fname4)), array=self.fname1) )
            colslist.append( fits.Column(name='MINVECTOR4', format='%iA' % max(map(len,self.minvector4)), array=self.minvector1) )
            colslist.append( fits.Column(name='MINRCHI24', format='E', array=self.minrchi24) )
            colslist.append( fits.Column(name='NPOLY4', format='J', array=self.npoly4) )
            colslist.append( fits.Column(name='NPIXSTEP4', format='J', array=self.npixstep4) )
            colslist.append( fits.Column(name='THETA4', format='%iA' % max(map(len,self.theta4)), array=self.theta1) )
            colslist.append( fits.Column(name='Z5', format='E', array=self.z5) )
            colslist.append( fits.Column(name='Z_ERR5', format='E', array=self.z_err5) )
            colslist.append( fits.Column(name='CLASS5', format='%iA' % max(map(len,self.class5)), array=self.class1) )
            colslist.append( fits.Column(name='SUBCLASS5', format='%iA' % max(map(len,self.subclass5)), array=self.subclass1) )
            colslist.append( fits.Column(name='FNAME5', format='%iA' % max(map(len,self.fname5)), array=self.fname1) )
            colslist.append( fits.Column(name='MINVECTOR5', format='%iA' % max(map(len,self.minvector5)), array=self.minvector1) )
            colslist.append( fits.Column(name='MINRCHI25', format='E', array=self.minrchi25) )
            colslist.append( fits.Column(name='NPOLY5', format='J', array=self.npoly5) )
            colslist.append( fits.Column(name='NPIXSTEP5', format='J', array=self.npixstep5) )
            colslist.append( fits.Column(name='THETA5', format='%iA' % max(map(len,self.theta5)), array=self.theta1) )
            colslist.append( fits.Column(name='', format='', array=) )
            colslist.append( fits.Column(name='', format='', array=) )
            colslist.append( fits.Column(name='', format='', array=) )
            colslist.append( fits.Column(name='', format='', array=) )
            colslist.append( fits.Column(name='', format='', array=) )
            colslist.append( fits.Column(name='', format='', array=) )
            colslist.append( fits.Column(name='', format='', array=) )
            




    def merge_chi2(self):
        
        try: topdir = environ['REDMONSTER_SPECTRO_REDUX']
        except: topdir = None
        try: run2d = environ['RUN2D']
        except: run2d = None
        try: run1d = environ['RUN1D']
        except: run1d = None
        chi2path = join( topdir, run2d, '%s' % self.plate, run1d, 'chi2arr-%s-%s-%s-*.fits' % (self.temp, self.plate, self.mjd) ) if topdir and run2d and run1d else None
        
        fiberid = []
        paths = []
        
        if chi2path:
            for file in iglob(chi2path):
                paths.append( file )
                m = re.search( 'chi2arr-%s-%s-%s-(\d+).fits' % (self.temp, self.plate, self.mjd), basename(file) )
                if m.group(1): fiberid.append( int(m.group(1)) )
            fiberid.sort()
            paths.sort()
            
            for i,path in enumerate(paths):
                chi2arr = fits.open(path)[0].data
                try:
                    chi2arrs
                except NameError:
                    chi2arrs = n.zeros( (len(fiberid),) + chi2arr.shape[1:] )
                    chi2arrs[i] = chi2arr
                else:
                    chi2arrs[i] = chi2arr
                remove(path)

            prihdu = fits.PrimaryHDU(chi2arrs)
            col1 = fits.Column(name='FIBERID', format='J', array=fiberid)
            cols = fits.ColDefs([col1])
            tbhdu = fits.BinTableHDU.from_columns(cols)
            thdulist = fits.HDUList([prihdu,tbhdu])
            thdulist.writeto( join( topdir, run2d, '%s' % self.plate, run1d, 'chi2arr-%s-%s-%s.fits' % (self.temp, self.plate, self.mjd) ), clobber=True)
