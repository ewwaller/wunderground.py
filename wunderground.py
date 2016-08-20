#! /usr/bin/python
"""
Obtain cuurent weather from Weather Underground

    Copyright 2015 Eric Waller

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""


from urllib.request import urlopen
import json
import time
import shelve
import os
import logging

PersistentStrorageFilename = os.environ['HOME'] + '/.wunderground'


class Weather:

    """ 
    Class for retrieving weather data from wunderground.com and printing those data
    """

    baseURL ='http://api.wunderground.com/api/%s/conditions/astronomy/q/%s.json'

    # Definition of the fields of interest.  Each field is a tuple of four items --
    #  (1) a tuple that defines a path to the field,
    #  (2) an string prefix that is printed before the field value,
    #  (3) a string that is printed after the field value and
    #  (4) a flag that, if not None, is a string that defines whether the
    #      field is valid for imperial or metric units. .
    
    # The tuple that defines the key path (first item in the field)
    # defines the path (tree) of keys for the field of interest.
    # The size of the tuples  for the keys are variable in length as
    # this json scheme uses multiple layers of hierarchical dictionaries.
    # All of the entries are keys that point to dictionaries with the
    # exception of the last, which is a key for something that is not a
    # dictionary (string, int, float,etc)
    
    
    fields=( ( ('current_observation','display_location','full') ,'Location : '   ,'\n'      ,None),
             ( ('current_observation','local_time_rfc822')       ,''              ,'\n'      ,None),
             ( ('current_observation','weather')                 ,'Condition : '  ,'\n'      ,None),
             ( ('current_observation','temperature_string')      ,'Temperature :' ,'\n'      ,None), 
             ( ('current_observation','relative_humidity')       ,'Humidity :'    ,' / '     ,None),
             ( ('current_observation','dewpoint_string')         ,'Dewpoint :'    ,'\n'      ,None), 
             ( ('current_observation','pressure_in')             ,'Pressure :'    ,' in hg. ','imperial'),
             ( ('current_observation','pressure_mb')             ,'Pressure :'    ,' mb '    ,'metric'),
             ( ('current_observation','pressure_trend')          ,'Trend '        ,'\n'      ,None),
             ( ('current_observation','visibility_mi')           ,'Visibility :'  ,'mi\n'    ,'imperial'),
             ( ('current_observation','visibility_km')           ,'Visibility :'  ,'km\n'    ,'metric'),
             ( ('current_observation','wind_dir')                ,'Wind: '        , ''       ,None),
             ( ('current_observation','wind_mph')                ,' @ '           ,' mph\n'  ,'imperial'),
             ( ('current_observation','wind_kph')                ,' @ '           ,' kph\n'  ,'metric'),
             ( ('current_observation','precip_today_string')     ,'precip :'      ,'\n'      ,None),
             ( ('moon_phase','phaseofMoon')                      ,'Moon : '       ,''        ,None), 
             ( ('moon_phase','percentIlluminated')               ,' '             ,'%\n'     ,None),
             ( ('sun_phase','sunrise','hour')                    ,'Sunrise : '    ,''        ,None), 
             ( ('sun_phase','sunrise','minute')                  ,':'             ,' ; '     ,None),
             ( ('sun_phase','sunset','hour')                     ,'Sunset : '     ,''        ,None),
             ( ('sun_phase','sunset','minute')                   ,':'             ,'\n'      ,None)
           )

    def __init__(self,theLocation,theKey,imperial):
        """ Instanciate a weather object
        
        theLocation : a string representing the geolocation
        theKey      : a string representing the Weather Underground API key 
        """

        self.location=theLocation
        self.key=theKey
        self.imperial = imperial
        logging.info("location set to %s "%self.location)
        logging.info("Units are %s"%( "imperial" if self.imperial else "metric"))
        logging.info("Fetching weather data using API key "+self.key)
      
    def GetWeather(self):
        """ Get the json information for the current location 

        returns:  A dictionary of items in the json file
        """
        url= self.baseURL % ( self.key , self.location )
        logging.info("Retrieving weather report from %s"%url)
        response =urlopen(url)
        theString = response.read().decode('utf-8')
        theDict= json.loads(theString)
        logging.debug("json response received:%s"%theString)
        if 'error' in theDict['response']:
            print("Error, Wunderground reports: %s"%theDict['response']['error']['description'])
            return(False)
        if 'results' in theDict['response']:
            print("The location is ambiguous.  Wunderground reports %i locations"%len(theDict['response']['results']))
            for x in theDict['response']['results']:
                for key,value in x.items():
                    print(value,end=',')
                print()
            return(False)
        return (theDict)

    def PrintReport(self,theWeather):
        """ Generate  a report of the current weather using 'interesting' json fields 

        theWeather : a dictionary of weather items (derived from the json report)
        Returns: None
        """
        
        logging.info("Generating report")
        for x in self.fields:
            theThing=theWeather
            for y in x[0]:
                theThing=theThing[y]
            if not type(theThing) is str:
                theThing=theThing.__str__()
            if not x[3] or (self.imperial and (x[3] == 'imperial')) or ((not self.imperial) and (x[3]=='metric')):
                print (x[1]+theThing,end=x[2])
        print("Weather data by Weather Underground\n(http://www.wunderground.com)")

def main():
    from argparse import ArgumentParser
    logFormat='%(relativeCreated)6dmS (%(threadName)s) %(levelname)s : %(message)s'

    # variable theParameters defines the command line options, where 
    # and how their data are stored, and define the relation
    # of the command line parameters to things that are stored in 
    # persistent storage. 
    # 
    #    Element 0 is the member name in the ArgumentPaser object,
    #    element 1 is the action, 
    #    element 2 is the short option name, 
    #    element 3 is the long option name,
    #    element 4 is the key name for storage in theShelve (None implies the value is not stored) 
    #    element 5 is the help string, and 
    #    element 6 is the error message if the element is not set (None implies it is not required)
        
    theParameters=(
          ('verbose'  ,'store_true'  ,'-v' ,'--verbose'  , None        ,"Generate information"                   ,None),
          ('debug'    ,'store_true'  ,'-d' ,'--debug'    , None        ,"Generate debugging information"         ,None),
          ('api_key'  ,'store'       ,'-k' ,'--key'      , 'APIkey'    ,"Set and store the API key"              ,"API key not set"),
          ('location' ,'store'       ,'-l' ,'--location' , 'location'  ,"Set and store the location"             ,"Location not set"),
          ('units'    ,'store_true'  ,'-i' ,'--imperial' , 'units'     ,"Set and store choice of Imperial units" ,"Units not set (Imperial/Metric)"),
          ('units'    ,'store_false' ,'-m' ,'--metric'   , 'units'     ,"Set and store choice of Metric units"   ,"Units not set (Imperial/Metric)"),
        )

    # open the persistent storage and create any missing keys
    
    theShelve = shelve.open(PersistentStrorageFilename)

    for x in  theParameters:
        if x[4] and  not x[4] in theShelve:
            theShelve[x[4]]=None
        
    # Handle all the command line nonsense. 
    # There are six options -- one is to set the location, one is to set the API key, two to set the
    # unit system that is desired, and two to set verbose and debug level reporting.
    # Defaults come from persistent storage
    
    description = "Fetch weather from Weather Underground"
    parser = ArgumentParser(description=description)

    [ parser.add_argument(x[2],x[3],action=x[1],dest=x[0],help=x[5] ,
                          default = theShelve[x[4]] if x[4] else False )
                          for x in theParameters ]
    
    args = parser.parse_args()

    # Set up the log function and enable the output if the user wants it

    if (args.verbose):
        logging.basicConfig(level=logging.INFO, format=logFormat)
    if (args.debug):
        logging.basicConfig(level=logging.DEBUG, format=logFormat)

    # If anything needs to be updated in persistent storage, then do so.

    for x in theParameters:
        if x[4] != None and ( theShelve[x[4]] != getattr(args,x[0]) ):
            theShelve[x[4]] = getattr(args,x[0])
            result = theShelve[x[4]]
            if type(result) != str:
                result = result.__str__()
            logging.info('Persistent storage updated: %s set to %s' % (x[4],result))
                
    # If we have all the data we need, then proceed, die otherwise

    [parser.error(x[6]) for x in theParameters if x[4] != None  if  theShelve[x[4]] == None]

    # Here is where the magic happens.
    
    weather = Weather(theShelve['location'],theShelve['APIkey'],theShelve['units'])
    theWeather = weather.GetWeather()
    if theWeather:
        weather.PrintReport(theWeather)
    logging.info("Done")
    theShelve.close()

if __name__ == "__main__":
    main()
