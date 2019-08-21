CREATE TABLE [mapinfo].[egrn](
	[Adr] [nvarchar](1000) NULL,
	[Area] [float] NULL,
	[Cn] [varchar](25) NULL,
	[Cat] [nvarchar](500) NULL,
	[Coast] [decimal](18, 2) NULL,
	[SP_GEOMETRY] [geometry] NULL,
	[Util] [nvarchar](250) NULL,
	[MI_STYLE] [varchar](254) NULL,
	[MI_PRINX] [int] PRIMARY KEY IDENTITY(1,1) NOT NULL
)
GO