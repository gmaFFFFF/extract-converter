﻿# coding: utf-8

import csv
import os
import shapefile

from itertools import chain, tee
from lxml import etree
from pathlib import Path


def is_numeric(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


def xpath_ns(expr, tree=None):
    '''
    Разбирает простой путь XPath и добавляет локальное пространство имен в том месте где оно не указано
    Источник: https://stackoverflow.com/questions/5572247/how-to-find-xml-elements-via-xpath-in-python-in-a-namespace-agnostic-way
    '''
    "Parse a simple expression and prepend namespace wildcards where unspecified."

    def qualFunc(path):
        if (not path
                or ':' in path
                or path == '.'
                or path[0] == '*' or path[0] == '@'
                or path[-1] == ')'
        ):
            return path

        if '[' in path:
            s = path.split('[')
            return '%s[%s' % (qualFunc(s[0]), '['.join(s[1:]))

        return '*[local-name() = "%s"]' % path

    if '|' in expr:
        expr = '|'.join(xpath_ns(n)['path'] for n in expr.split('|'))
    else:
        expr = '/'.join(qualFunc(n) for n in expr.split('/'))
    nsmap = dict((k, v) for k, v in tree.nsmap.items() if k) if tree is not None else None

    return {'path': expr, 'namespaces': nsmap}


def mpolygonList2wkt(mpolygon, swapXY=False):
    if not mpolygon:
        return None
    wktMPgn = "MULTIPOLYGON ({0})"
    wktPgn = "({0})"
    wktLin = "({0})"
    wktPnt = "{1} {0}" if swapXY else "{0} {1}"

    pnt = lambda lin: (wktPnt.format(x, y) for x, y in lin)
    lin = lambda pgn: (wktLin.format(', '.join(pnt(linearRing))) for linearRing in pgn)
    pgn = lambda mpgn: (wktPgn.format(', '.join(lin(polygon))) for polygon in mpolygon)
    mpgn = lambda mpgnL: wktMPgn.format(', '.join(pgn(mpgn)))

    return mpgn(mpolygon)


def LandCategoryCode2Text(code: str) -> str:
    return LandCategoryCode2Text.cat.get(code, code)


LandCategoryCode2Text.cat: dict = {"003001000000": "Земли сельскохозяйственного назначения",
                                   "003002000000": "Земли населённых пунктов",
                                   "003003000000": "Земли промышленности",
                                   "003004000000": "Земли особо охраняемых территорий и объектов",
                                   "003005000000": "Земли лесного фонда",
                                   "003006000000": "Земли водного фонда",
                                   "003007000000": "Земли запаса",
                                   "003008000000": "Прочие земли"}


class RosreestrKPTReader:
    def __init__(self, pathToXml):
        self.parcelsXPathText = '|'.join(['//Parcel', '//land_record'])
        self.kpt = etree.parse(pathToXml)
        self.parcelsXPath = xpath_ns(self.parcelsXPathText, self.kpt.getroot())
        self.parcelsXPathFunc = etree.XPath(**self.parcelsXPath)

    def GetParcels(self):
        try:
            next((RosreestrParcelReader(p) for p in self.parcelsXPathFunc(self.kpt)))
        except StopIteration:
            return None

        return (RosreestrParcelReader(p) for p in self.parcelsXPathFunc(self.kpt))

    def GetFieldNames(self):
        return ['CN', 'Area', 'Coast', 'Cat', 'Util', 'Adr', "SP_GEOMETRY"]

    def ExportToCsv(self, csvFile, addHeader=False):

        parcels = self.GetParcels()
        if not parcels:
            return

        # Убрать столбец с геометрией в формате wkt
        parcels_without_geom = ({k: v for (k, v) in p.ToDict().items() if k != "SP_GEOMETRY"} for p in parcels)
        parcels_without_geom, parcels_without_geom_copy = tee(parcels_without_geom)

        field_names = self.GetFieldNames()
        field_names.remove("SP_GEOMETRY")

        writer = csv.DictWriter(csvFile, fieldnames=field_names)

        if addHeader:
            writer.writeheader()

        for p in parcels_without_geom:
            writer.writerow(p)

    def ExportToMsSql(self, sqlFile, tableName="TableName"):

        parcels = self.GetParcels()
        if not parcels:
            return

        field_names = self.GetFieldNames()

        def next_row():
            parcels_dict = ({k: v for k, v in p.ToDict().items()}
                            for p in parcels)
            for p in parcels_dict:
                row = []
                for field in field_names:
                    if field == "SP_GEOMETRY":
                        row.append(f"geometry::STGeomFromText('{mpolygonList2wkt(p[field])}',0)"
                                   if p[field] else "Null")
                    elif is_numeric(p[field]):
                        row.append(p[field])
                    elif p[field] == "":
                        row.append("Null")
                    else:
                        row.append(f"'{p[field]}'")
                yield row
            return

        field_names_str = ','.join(f'"{field}"' for field in field_names)
        for p in next_row():
            parcels_row_text = ','.join(p)
            sqlFile.write(f"INSERT INTO {tableName} ({field_names_str}) ")
            sqlFile.write(f"Values ({parcels_row_text}) ")
            sqlFile.write("\nGO\n")

    def ExportToShp(self, shpFile):

        parcels = self.GetParcels()
        if not parcels:
            return

        field_names = self.GetFieldNames()
        field_names.remove("SP_GEOMETRY")
        field_names.remove("Adr")

        if not shpFile.fields:
            # Данный код не работает. Происходит переполнение полей
            #	for fn in fieldNames:
            #		shpFile.field(fn, "C", 254)
            shpFile.field("CN", "C", 25)
            shpFile.field("Area", "N")
            shpFile.field("Coast", decimal=2)

        for p in parcels:
            shpFile.record(**p.ToDict())
            contours = p.ToDict()["SP_GEOMETRY"] if p.ToDict()["SP_GEOMETRY"] else None
            cont_vertex_reversed = [list(reversed(ring)) for cnt in contours for ring in cnt] if contours else None
            geom = cont_vertex_reversed if cont_vertex_reversed else None
            shpFile.poly(geom) if geom else shpFile.null()

    def DebugPrint(self):
        '''
        for p in self.parcels:
            for e in p.ToDict():
                print('%s-%s'%(e,p.ToDict()[e]))

        for p in self.parcels:
            print(p.ToDict()['КН'])
            print(mpolygonList2wkt(p.ToDict()['SP_GEOMETRY']))
        '''


class RosreestrParcelReader:
    swapXY = True

    parcelCadNumXPathText = '|'.join(['./@CadastralNumber', './object/common_data/cad_number/text()'])
    parcelAreaXPathText = '|'.join(['./Area/Area', './params/area/value'])
    parcelAdressXPathText = '|'.join(['./Location/Address/Note', './address_location/address/readable_address'])
    parcelCategoryXPathText = '|'.join(['./Category', './params/category/type/code'])
    parcelUtilizationXPathText = '|'.join(
        ['./Utilization/@ByDoc', './params/permitted_use/permitted_use_established/by_document/text()'])
    parcelCadastralCostXPathText = '|'.join(['./CadastralCost/@Value', './cost/value/text()'])
    parcelMPolygonGeomXPathText = '|'.join(
        ['./Contours/Contour/EntitySpatial', './EntitySpatial', './contours_location/contours/contour/entity_spatial'])
    parcelLinearRingGeomXPathText = '|'.join(['./SpatialElement', './spatials_elements/spatial_element'])
    parcelPointGeomXPathText = '|'.join(['./SpelementUnit/Ordinate', './ordinates/ordinate'])
    parcelPointXCoordXPathText = '|'.join(['./@X', './x/text()'])
    parcelPointYCoordXPathText = '|'.join(['./@Y', './y/text()'])

    def __init__(self, Xml):

        self.parcel = Xml

        root = self.parcel.getroottree().getroot()

        self.parcelCadNumXPath = xpath_ns(self.parcelCadNumXPathText, root)
        self.parcelCadNumXPathFunc = etree.XPath(**self.parcelCadNumXPath)

        self.parcelAreaXPath = xpath_ns(self.parcelAreaXPathText, root)
        self.parcelAreaXPathFunc = etree.XPath(**self.parcelAreaXPath)

        self.parcelAdressXPath = xpath_ns(self.parcelAdressXPathText, root)
        self.parcelAdressXPathFunc = etree.XPath(**self.parcelAdressXPath)

        self.parcelCategoryXPath = xpath_ns(self.parcelCategoryXPathText, root)
        self.parcelCategoryXPathFunc = etree.XPath(**self.parcelCategoryXPath)

        self.parcelUtilizationXPath = xpath_ns(self.parcelUtilizationXPathText, root)
        self.parcelUtilizationXPathFunc = etree.XPath(**self.parcelUtilizationXPath)

        self.parcelCadastralCostXPath = xpath_ns(self.parcelCadastralCostXPathText, root)
        self.parcelCadastralCostXPathFunc = etree.XPath(**self.parcelCadastralCostXPath)

        self.parcelMPolygonGeomXPath = xpath_ns(self.parcelMPolygonGeomXPathText, root)
        self.parcelMPolygonGeomXPathFunc = etree.XPath(**self.parcelMPolygonGeomXPath)

        self.parcelLinearRingGeomXPath = xpath_ns(self.parcelLinearRingGeomXPathText, root)
        self.parcelLinearRingGeomXPathFunc = etree.XPath(**self.parcelLinearRingGeomXPath)

        self.parcelPointGeomXPath = xpath_ns(self.parcelPointGeomXPathText, root)
        self.parcelPointGeomXPathFunc = etree.XPath(**self.parcelPointGeomXPath)

        self.parcelPointXCoordXPath = xpath_ns(self.parcelPointXCoordXPathText, root)
        self.parcelPointXCoordXPathFunc = etree.XPath(**self.parcelPointXCoordXPath)

        self.parcelPointYCoordXPath = xpath_ns(self.parcelPointYCoordXPathText, root)
        self.parcelPointYCoordXPathFunc = etree.XPath(**self.parcelPointYCoordXPath)

        self.Parse()

    def Parse(self):

        self.parcelDict = {}
        self.ParseSemantics()
        self.ParseGeom()

    def ParseSemantics(self):
        self.parcelDict['CN'] = self.parcelCadNumXPathFunc(self.parcel)[0] if self.parcelCadNumXPathFunc(
            self.parcel) else ''
        self.parcelDict['Area'] = self.parcelAreaXPathFunc(self.parcel)[0].text if self.parcelAreaXPathFunc(
            self.parcel) else ''
        self.parcelDict['Adr'] = self.parcelAdressXPathFunc(self.parcel)[0].text if self.parcelAdressXPathFunc(
            self.parcel) else ''
        cat = self.parcelCategoryXPathFunc(self.parcel)[0].text if self.parcelCategoryXPathFunc(self.parcel) else ''
        self.parcelDict['Util'] = self.parcelUtilizationXPathFunc(self.parcel)[0] if self.parcelUtilizationXPathFunc(
            self.parcel) else ''
        self.parcelDict['Coast'] = self.parcelCadastralCostXPathFunc(self.parcel)[
            0] if self.parcelCadastralCostXPathFunc(self.parcel) else ''

        self.parcelDict['Cat'] = LandCategoryCode2Text(cat)

    def ParseGeomElem(self, xml, parser):
        geomElementsXml = parser(xml)
        if not geomElementsXml:
            return None

        geomElements = []
        for g in geomElementsXml:
            geomElements.append(g)

        return geomElements

    def ParseGeom(self):
        self.parcelDict['SP_GEOMETRY'] = self.ParsePolygon(self.parcel)

    def ParsePolygon(self, parcel):
        polygonsXml = self.ParseGeomElem(parcel, self.parcelMPolygonGeomXPathFunc)

        if not polygonsXml:
            return None

        mpolygon = []
        for p in polygonsXml:
            mpolygon.append(self.ParseLinearRing(p))

        return mpolygon

    def ParseLinearRing(self, polygonXml):
        linearRingsXml = self.ParseGeomElem(polygonXml, self.parcelLinearRingGeomXPathFunc)
        if not linearRingsXml:
            return None

        linearRings = []
        for p in linearRingsXml:
            linearRings.append(self.ParsePoints(p))

        return linearRings

    def ParsePoints(self, linearRingXml):
        pointsXml = self.ParseGeomElem(linearRingXml, self.parcelPointGeomXPathFunc)
        if not pointsXml:
            return None

        points = []
        for p in pointsXml:
            x, y = float(self.parcelPointXCoordXPathFunc(p)[0]), float(self.parcelPointYCoordXPathFunc(p)[0])
            points.append((y, x) if self.swapXY else (x, y))

        return points

    def ToDict(self):
        return self.parcelDict


def GetListXmlFile(parentFolder):
    '''
    Создает список, содержащий xml-файлы
    '''
    listXmlFiles = []

    for dirname, dirnames, filenames in os.walk(parentFolder):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() == '.xml':
                fullName = os.path.join(dirname, filename).lower()
                listXmlFiles.append(fullName)

    listXmlFiles.sort()

    return listXmlFiles


def main():
    print('Run')

    parentFolder = Path().absolute() / 'in'
    csvPath = Path().absolute() / r'out\attrib.csv'
    shpPath = Path().absolute() / r'out\geom'
    sqlPath = Path().absolute() / r'out\query.sql'
    listXml = GetListXmlFile(parentFolder)

    with open(csvPath, 'w', newline='', buffering=-1) as csvFile, \
            open(sqlPath, 'w', buffering=-1) as sqlFile, \
            shapefile.Writer(target=str(shpPath), shapeType=shapefile.POLYGON) as shpFile:

        for xml in listXml:
            print(xml)

            KPTReader = RosreestrKPTReader(xml)

            if listXml[0] == xml:
                KPTReader.ExportToCsv(csvFile, True)
            else:
                KPTReader.ExportToCsv(csvFile, False)

            KPTReader.ExportToShp(shpFile)
            KPTReader.ExportToMsSql(sqlFile, "mapinfo.egrn")

    print('Complete')


main()
