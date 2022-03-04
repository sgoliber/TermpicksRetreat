# -*- coding: utf-8 -*-
"""
Created on Tue Sep 14 14:40:16 2021

@author: sofyg
"""

from shapely.ops import nearest_points
import numpy as np
from shapely.geometry import LineString
from shapely.geometry import Point, MultiPoint
import pandas as pd
import datetime as dt


def redistribute_vertices(geom, distance):
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


def near(centroid,centerline,valuedf = 'geometry'):
    unary_union = centerline.unary_union
    nearest = centerline['geometry']== nearest_points(centroid,unary_union)[1]
    nearest_np = nearest.to_numpy()
    value = np.where(nearest_np == True)[0][0]
    id_num = centerline[valuedf].iloc[value]

    return id_num




def points_along_trace(GlacierID,Traces,n_vert=150):
    errfile = 'Errors/'+str(GlacierID) +'err.txt'
    f = open(errfile, "w")
    f.write("Created file")

    #Number of verticies to redistribute


    shpDF = Traces[Traces['GlacierID']==GlacierID]
    #shpDF = shpDF.sort_values(by=['Date'])

    #POINTS ALONG TRACE
    pointsList = []
    dropList = []
    for i,r in shpDF.iterrows():
        if r.geometry.type == 'MultiLineString':
            point_r = []
            exploded = r.explode()
            segs = len(exploded.geometry)
            for i in range(0,segs):
                multiline_r = redistribute_vertices(exploded.geometry[i],150)
                for coord in multiline_r.coords:
                    point_r.append(coord)
            points = MultiPoint(point_r)
            pointsList.append(points)

        else:
            multiline = r['geometry']
            multiline_r = redistribute_vertices(multiline, n_vert)
            point_r = []
            for coord in multiline_r.coords:
                point_r.append(coord)
            points = MultiPoint(point_r)
            pointsList.append(points)
        
    with open(errfile, 'w') as filehandle:
        filehandle.writelines("%s\n" % ind for ind in dropList)

    shpDF['points'] = pointsList
   # shpDF = shpDF.drop(dropList)
    del shpDF['geometry']
    shpDF = shpDF.rename(columns={"points": "geometry"})
    shpDF.set_geometry(col='geometry', inplace=True)
    return shpDF


def mean_trace_loc(shpDF,centerline):
    meanlocs = []
    dates = shpDF['Date'].to_list()
    auths = shpDF['Author'].to_list()
    geoms = shpDF['geometry'].to_list()
    for line in geoms:
        allpoints = []
        for point in line:
            pp = near(point,centerline,valuedf='geometry')
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


def calc_retreat(GlacierID,newDF,centerline,location='Retreat'):
    
    nearestCL = []
    for point in newDF['geometry']:
        pp = near(point,centerline,valuedf='cumsum')
        nearestCL.append(pp)

    #CALCULATE THE RETREAT
    retreat = []
    for i in range(len(nearestCL)):
        r = nearestCL[0] - nearestCL[i] 
        retreat.append(r)

    dates = newDF['Date'].to_list()
    datelist=[]
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

    df.to_csv(location+'\\'+str(GlacierID)+'.csv')
    
    return df
