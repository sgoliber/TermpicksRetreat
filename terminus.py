# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 14:19:39 2022

@author: sofyg
"""
from shapely.ops import nearest_points
import numpy as np
from shapely.geometry import LineString
from shapely.geometry import Point, MultiPoint
import pandas as pd
import datetime as dt
import geopandas as gpd

#Inputs
#Terminus Picks Labled by the glacier ID
#Glacier Centerlines



def redistribute_vertices(geom, distance):
    #INPUT: Linestring Geometry, distance between interpolated points
    #OUTPUT: Linetring geometry with evenly spaced vertices along line 
        
    if geom.geom_type == 'LineString':
        num_vert = int(round(geom.length / distance))
        if num_vert == 0:
            num_vert = 1
        return LineString(
            [geom.interpolate(float(n) / num_vert, normalized=True)
             for n in range(num_vert + 1)])
    elif geom.geom_type == 'MultiLineString':
        parts = [redistribute_vertices(part, distance)
                 for part in geom]
        return type(geom)([p for p in parts if not p.is_empty])
    else:
        raise ValueError('unhandled geometry %s', (geom.geom_type,))
        
        
def Average(lst): 
    return sum(lst) / len(lst) 



class termpicks_trace:
    #INPUT: Termpicks Traces, GlacierID of interest
    
    def __init__(self, dataframe,glacid):
        #Subset terminus picks in TermPicks data by Glacier ID
        
        self.data = dataframe[dataframe['GlacierID']==glacid].copy()
        self.glacid = glacid
        
    
    #Interpolate evenly spaced points at redistibuted vertices along a line, n_vert is in meters
    def trace2points(self,n_vert=30):
        #Number of verticies to redistribute

        shpDF = self.data
        shpDF = shpDF.sort_values(by=['Date'])

        #initalize list of points along geometry
        pointsList = []
        #iterate over each terminus trace
        for i,r in shpDF.iterrows():
            #Multi-line/split termini Multilinestrings
            if r.geometry.type == 'MultiLineString':
                point_r = []
                
                #Split geometries in multiline string
                exploded = r.explode()
                segs = len(exploded.geometry)
                
                #for each segment, redistibute vertices
                for i in range(0,segs):
                    multiline_r = redistribute_vertices(exploded.geometry[i],n_vert)
                    #save each vertex as a coordiante
                    for coord in multiline_r.coords:
                        point_r.append(coord)
                        
                #turn list of coordiantes into a multipoint feature
                points = MultiPoint(point_r)
                pointsList.append(points)

            else:
                #Same process as aobve, but for single Linestrings
                singleline = r['geometry']
                singleline_r = redistribute_vertices(singleline, n_vert)
                point_r = []
                for coord in singleline_r.coords:
                    point_r.append(coord)
                points = MultiPoint(point_r)
                pointsList.append(points)
            
    
        #create new dataframe with points along geometry in place of 
        #linestrings
        
        shpDF['points'] = pointsList
        del shpDF['geometry']
        terminus_points = shpDF.rename(columns={"points": "geometry"})
        terminus_points.set_geometry(col='geometry', inplace=True)
        
        return terminus_points


class termpicks_centerline:
    #INPUT: Termpicks Centerlines, GlacierID of interest
    
    def __init__(self, dataframe ,glacid):
        self.data = dataframe[dataframe['GlacierID']==glacid].copy()
        self.glacid = glacid

        #Interpolate evenly spaced points at redistibuted vertices along a
        #centerline
    def line2points(self,n_vert):
        shpDF = self.data
        
        #Get geometry of the centerline of intrest
        singleline = shpDF['geometry'].iloc[0]
        #Redistibute vertices
        singleline_r = redistribute_vertices(singleline, n_vert)
        point_r = []
        #export each coordiate of the redistributed vertices 
        for coord in singleline_r.coords:
            point_r.append(coord)
        points = MultiPoint(point_r)
    
        #save each x,y as an individual point per row
        geos = [Point(p.x, p.y) for p in points]
        centerline_points = gpd.GeoDataFrame(geometry = geos, crs="EPSG:3413")
        
        #calculate distance between points and save as distance column
        centerline_points['distance'] = centerline_points.distance(centerline_points.shift())
        #calculate cumsum of distances between points and save as cumsum column
        centerline_points['cumsum'] = centerline_points['distance'].cumsum()
        
        return centerline_points
        
    
    
class termpicks_interpolation:
    #INPUT: output from termpicks_points, output from termpicks_centerline
        
    def __init__(self, terminus_points, centerline_points):
        self.termini = terminus_points
        self.centerline = centerline_points
        self.count = len(terminus_points)
        
    #Find nearest point to a dataframe of points
    def near(self,centroid,centerline_points,valuedf):
        #INPUT: point, centerline with interpolted points 
        #OUTPUT
        
        unary_union = centerline_points.unary_union
        nearest = centerline_points['geometry']== nearest_points(centroid,unary_union)[1]
        nearest_np = nearest.to_numpy()
        value = np.where(nearest_np == True)[0][0]
        id_num = centerline_points[valuedf].iloc[value]

        return id_num
    
    #Find the mean trace location of a terminus 
    def mean_trace_loc(self):
        
        meanlocs = []
        dates = self.termini['Date'].to_list()
        auths = self.termini['Author'].to_list()
        geoms = self.termini['geometry'].to_list()
        for line in geoms:
            allpoints = []
            for point in line:
                val = 'geometry'
                pp = self.near(point,self.centerline,val)
                allpoints.append(pp)
        
            ax=[]
            ay=[]
            for i in allpoints:
                ax.append(i.x)
                ay.append(i.y)
            meanlocs.append([Average(ax),Average(ay)])
            
        newpts = []
        for i in meanlocs:
            newpts.append(Point(i))
        newDF = pd.DataFrame()
        newDF['geometry'] = newpts
        newDF['Date'] = dates
        newDF['Author'] = auths
        
        return  newDF   
    
    #Get the closest point in the centerline to the mean location
    #Calculate the retreat from the cumulative distance along the terminus
    #Date determines what the inital '0' pick is, otherwse its the earliest 
    #avalible pick
    def calc_retreat(self):
        
        newDF = self.mean_trace_loc()
        
        nearestCL = []
        for point in newDF['geometry']:
            pp = self.near(point,self.centerline,valuedf='cumsum')
            nearestCL.append(pp)
    
        #CALCULATE THE RETREAT
        retreat = []
        for i in range(len(nearestCL)):
            r = nearestCL[0] - nearestCL[i] 
            retreat.append(r)
    
        dates = newDF['Date'].to_list()
        datelist=[]
        #Some termpicks data is year only, place it in the middle of the year
        ##TO DO: option to remove these if intrested in seasonality**
        for i in dates:
            year = i[0:4]
            month = i[5:7]
            day = i[8:10]
            if month == '00':
                month = '07'
                day = '02'
            datelist.append(year+'-'+month+'-'+day)
    
        dts = [dt.datetime.strptime(date, '%Y-%m-%d').date() for date in datelist]
    
        df = pd.DataFrame(list(zip(dts,nearestCL, retreat)),
                   columns =['date', 'position', 'retreat'])
    
        df['Author'] = newDF['Author'].to_list()
    

        
        return df
        
