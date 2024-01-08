<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
	<xsl:output encoding="utf-8" method="text"/>
	<xsl:param name="xy" select="false()"/>
	<xsl:param name="acad" select="false()"/>
	<xsl:variable name="yx" select="(true() and not($xy)) or (false() and $xy)" /> 

	<!-- Служебные. Начало -->
	<xsl:variable name="cmd_start">
		<xsl:text>(VL-CMDF </xsl:text>
	</xsl:variable>

	<xsl:variable name="pline_start">
		<xsl:choose>
			<xsl:when test="$acad">
				<xsl:text>"_pline"</xsl:text>
			</xsl:when>
			<xsl:otherwise>
				<xsl:text>"pline"</xsl:text>
			</xsl:otherwise>
		</xsl:choose>
		<xsl:text> </xsl:text>
	</xsl:variable>

	<xsl:variable name="point_start">
		<xsl:choose>
			<xsl:when test="$acad">
				<xsl:text>"_point"</xsl:text>
			</xsl:when>
			<xsl:otherwise>
				<xsl:text>"point"</xsl:text>
			</xsl:otherwise>
		</xsl:choose>
		<xsl:text> </xsl:text>
	</xsl:variable>

	<xsl:variable name="cmd_end">
		<xsl:choose>
			<xsl:when test="$acad">
				<xsl:text>"\e") </xsl:text>
				<xsl:text>&#xa;</xsl:text>
			</xsl:when>
			<xsl:otherwise>
				<xsl:text>"\e") </xsl:text>
			</xsl:otherwise>
		</xsl:choose>

	</xsl:variable>


	<xsl:variable name="prolog">
		<xsl:text>(vl-load-com)</xsl:text>	
		<xsl:text>&#xa;</xsl:text>	 
		<xsl:if test="$acad">
			<!-- Временно отключаем привязку -->
			<xsl:text>(setvar "osmode" 16384)</xsl:text>
			<xsl:text>&#xa;</xsl:text>
		</xsl:if>
	</xsl:variable>

	<xsl:variable name="epilog">
		<xsl:if test="$acad">
			<!-- Восстанавливаем привязку -->
			<xsl:text>(setvar "osmode" 16383)</xsl:text>
			<xsl:text>&#xa;</xsl:text>
		</xsl:if>
	</xsl:variable>
	<!-- Служебные. Конец -->

	<!-- Старт. Начало -->
	<xsl:template match="/" name="run">
		<xsl:value-of select="$prolog"/>
		<xsl:apply-templates/>
		<xsl:value-of select="$epilog"/>
	</xsl:template>
	<!-- Старт. Конец -->

	<!-- Схема расположения и межевик. Начало -->
	<xsl:template match="*[local-name() = 'Spatial_Element'] | *[local-name() = 'SpatialElement']
		| *[local-name() = 'SpecifyRelatedParcel']">
		<xsl:value-of select="$cmd_start"/>
		<xsl:value-of select="$pline_start"/>
		<xsl:apply-templates/>
		<xsl:value-of select="$cmd_end"/>
	</xsl:template>

	<xsl:template match="*[local-name() = 'NewOrdinate'] | *[local-name() = 'Ordinate']">
		<xsl:text>'(</xsl:text>
		<xsl:choose>
			<xsl:when test="$yx">
				<xsl:value-of select="@Y"/>
				<xsl:text> </xsl:text>
				<xsl:value-of select="@X"/>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="@X"/>
				<xsl:text> </xsl:text>
				<xsl:value-of select="@Y"/>
			</xsl:otherwise>
		</xsl:choose>
		<xsl:text>) </xsl:text>
		<xsl:apply-templates/>
	</xsl:template>
	<!-- Схема расположения и межевик. Конец -->

	<!-- Выписка. Начало -->
	<xsl:template
		match="
			contours_location/contours/contour/entity_spatial/spatials_elements/spatial_element |
			build_record/contours/contour/entity_spatial/spatials_elements/spatial_element |
			construction_record/contours/contour/entity_spatial/spatials_elements/spatial_element
			">
		<xsl:value-of select="$cmd_start"/>
		<xsl:choose>
			<xsl:when test="count(ordinates/ordinate) > 1">
				<xsl:value-of select="$pline_start"/>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="$point_start"/>
			</xsl:otherwise>
		</xsl:choose>

		<xsl:apply-templates select="ordinates/ordinate" mode="obj"/>

		<xsl:value-of select="$cmd_end"/>
	</xsl:template>

	<xsl:template match="ordinate" mode="obj">
		<xsl:text>'(</xsl:text>
		<xsl:choose>
			<xsl:when test="$yx">
				<xsl:value-of select="y/text()"/>
				<xsl:text> </xsl:text>
				<xsl:value-of select="x/text()"/>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="x/text()"/>
				<xsl:text> </xsl:text>
				<xsl:value-of select="y/text()"/>
			</xsl:otherwise>
		</xsl:choose>
		<xsl:text>) </xsl:text>
		<xsl:apply-templates/>
	</xsl:template>
	<!-- Выписка. Конец -->

	<!-- Подавить вывод содержимого элементов -->
	<xsl:template match="text()"/>
</xsl:stylesheet>
