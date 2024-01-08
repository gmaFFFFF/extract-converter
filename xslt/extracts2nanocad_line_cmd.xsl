<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
	<xsl:import href="extract2nanocad_line_cmd.xsl"/>	
	<xsl:output encoding="utf-8" method="text"/>	
	
	<!-- Старт. Начало -->
	<xsl:template match="/">
		<xsl:apply-templates select="//file"/>
	</xsl:template>
	
	<xsl:template match="/" mode="file">
		<xsl:call-template name="run" /> 
	</xsl:template>
	
	<xsl:template match="file[@href]">
		<xsl:text>;File: "</xsl:text>
		<xsl:value-of select="@href"/>
		<xsl:text>"&#xa;</xsl:text>
		<xsl:apply-templates select="document(@href,.)" mode="file"/>
		<xsl:text>&#xa;</xsl:text>		
	</xsl:template>

</xsl:stylesheet>	