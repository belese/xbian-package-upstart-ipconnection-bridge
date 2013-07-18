xbian-package-upstart-xbmc-bridge
=================================

bridge between xbmc and upstart
    
upstart event :
---------------
      screensaver :
             send when xbmcscreensaver is activate/deactivate
             env variable : 
                ACTION = START/STOP
       player :
             send when player is start/stop/pause
             env variable :
                ACTION = PLAY/STOP/PAUSE
                TYPE = MOVIE/TVSHOW/AUDIO/NONE (to be check on xbmc api)
       library :
             send when action on library :
             env variable :
                ACTION = START/STOP/UPDATED
                MODE = UPDATE/CLEAN/NONE
                TYPE = AUDIO/VIDEO      
       
       xbmcplevel :
              send when xbmc change his level
              env variable  :
                 LEVEL = [012345]
                    0 : xbmc is stopped    
                    1 : xbmc very low priority (screensaver activated and player stop and library stop)
                    2 : xbmc low priority (screensaver activated and (player start or library start))
                    3 : xbmc normal priority (screensaver deactivated and player stop and library stop)
                    4 : xbmc high priotity (screensaver deactivated and (player start xor library start))
                    5 : xbmc very high priotity (screensaver deactivated and player start and library start)
                 PREVLEVEL = [012345] 
                    Previous xbmc level
