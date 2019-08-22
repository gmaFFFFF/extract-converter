# coding: utf-8
'''
MIT License

Copyright © 2017 Гришкин Максим (FFFFF@bk.ru) 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


Текст лицензии на русском языке.
Ограничение перевода: Это неофициальный перевод, 
он взят с сайта: http://licenseit.ru/wiki/index.php/MIT_License 
В случаях любого несоответствия перевода исходному тексту лицензии 
на английском языке верным считается текст на английском языке.

Copyright © 2017 Гришкин Максим (FFFFF@bk.ru) 
Данная лицензия разрешает, безвозмездно, лицам, получившим копию данного программного 
обеспечения и сопутствующей документации (в дальнейшем именуемыми "Программное Обеспечение"), 
использовать Программное Обеспечение без ограничений, включая неограниченное право 
на использование, копирование, изменение, объединение, публикацию, распространение, 
сублицензирование и/или продажу копий Программного Обеспечения, также как и лицам, 
которым предоставляется данное Программное Обеспечение, при соблюдении следующих условий:

Вышеупомянутый копирайт и данные условия должны быть включены во все копии 
или значимые части данного Программного Обеспечения.

ДАННОЕ ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ ПРЕДОСТАВЛЯЕТСЯ «КАК ЕСТЬ», БЕЗ ЛЮБОГО ВИДА ГАРАНТИЙ, 
ЯВНО ВЫРАЖЕННЫХ ИЛИ ПОДРАЗУМЕВАЕМЫХ, ВКЛЮЧАЯ, НО НЕ ОГРАНИЧИВАЯСЬ ГАРАНТИЯМИ ТОВАРНОЙ 
ПРИГОДНОСТИ, СООТВЕТСТВИЯ ПО ЕГО КОНКРЕТНОМУ НАЗНАЧЕНИЮ И НЕНАРУШЕНИЯ ПРАВ. 
НИ В КАКОМ СЛУЧАЕ АВТОРЫ ИЛИ ПРАВООБЛАДАТЕЛИ НЕ НЕСУТ ОТВЕТСТВЕННОСТИ 
ПО ИСКАМ О ВОЗМЕЩЕНИИ УЩЕРБА, УБЫТКОВ ИЛИ ДРУГИХ ТРЕБОВАНИЙ ПО ДЕЙСТВУЮЩИМ КОНТРАКТАМ, 
ДЕЛИКТАМ ИЛИ ИНОМУ, ВОЗНИКШИМ ИЗ, ИМЕЮЩИМ ПРИЧИНОЙ ИЛИ СВЯЗАННЫМ С ПРОГРАММНЫМ 
ОБЕСПЕЧЕНИЕМ ИЛИ ИСПОЛЬЗОВАНИЕМ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ 
ИЛИ ИНЫМИ ДЕЙСТВИЯМИ С ПРОГРАММНЫМ ОБЕСПЕЧЕНИЕМ.
'''

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
        self.parcelsXPathText = '//Parcel|//land_record'
        self.kpt = etree.parse(pathToXml)
        self.parcelsXPath = xpath_ns(self.parcelsXPathText, self.kpt.getroot())
        self.parcelsXPathFunc = etree.XPath(**self.parcelsXPath)

        self.ParseParcel()

    def ParseParcel(self):
        self.parcels = [RosreestrParcelReader(p) for p in self.parcelsXPathFunc(self.kpt)]

        return self.parcels

    def ExportToCsv(self, csvFile, addHeader=False):
        if not self.parcels:
            return

        # Убрать столбец с геометрией в формате wkt
        parcels_without_geom = ({k: v for (k, v) in p.ToDict().items() if k != "SP_GEOMETRY"} for p in self.parcels)
        parcels_without_geom, parcels_without_geom_copy = tee(parcels_without_geom)

        fieldNames = sorted(next(parcels_without_geom_copy).keys())
        writer = csv.DictWriter(csvFile, fieldnames=fieldNames)

        if addHeader:
            writer.writeheader()

        for p in parcels_without_geom:
            writer.writerow(p)

        print('В csv добавлено %d участка(ов)' % len(self.parcels))

    def ExportToMsSql(self, sqlFile, tableName="TableName"):

        if not self.parcels:
            return

        field_names = sorted(self.parcels[0].ToDict().keys())

        def next_row():
            parcels_dict = ({k: v for k, v in p.ToDict().items()}
                            for p in self.parcels)
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
        if not self.parcels:
            return

        fieldNames = sorted(self.parcels[0].ToDict().keys())
        fieldNames.remove("SP_GEOMETRY")
        fieldNames.remove("Adr")

        if not shpFile.fields:
            # Данный код не работает. Происходит переполнение полей
            #	for fn in fieldNames:
            #		shpFile.field(fn, "C", 254)
            shpFile.field("CN", "C", 25)
            shpFile.field("Area", "N")
            shpFile.field("Coast", decimal=2)

        for p in self.parcels:
            shpFile.record(**p.ToDict())
            geom = list(chain(*p.ToDict()["SP_GEOMETRY"])) if p.ToDict()["SP_GEOMETRY"] else None
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

    parcelCadNumXPathText = './@CadastralNumber|./object/common_data/cad_number/text()'
    parcelAreaXPathText = './Area/Area|./params/area/value'
    parcelAdressXPathText = './Location/Address/Note|./address_location/address/readable_address'
    parcelCategoryXPathText = './Category|./params/category/type/code'
    parcelUtilizationXPathText = './Utilization/@ByDoc|./params/permitted_use/permitted_use_established/by_document/text()'
    parcelCadastralCostXPathText = './CadastralCost/@Value|./cost/value/text()'
    parcelMPolygonGeomXPathText = './Contours/Contour/EntitySpatial|./EntitySpatial|./contours_location/contours/contour/entity_spatial'
    parcelLinearRingGeomXPathText = './SpatialElement|./spatials_elements/spatial_element'
    parcelPointGeomXPathText = './SpelementUnit/Ordinate|./ordinates/ordinate'
    parcelPointXCoordXPathText = './@X|./x/text()'
    parcelPointYCoordXPathText = './@Y|./y/text()'

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

    with open(csvPath, 'w', newline='') as csvFile, \
            open(sqlPath, 'w') as sqlFile, \
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
