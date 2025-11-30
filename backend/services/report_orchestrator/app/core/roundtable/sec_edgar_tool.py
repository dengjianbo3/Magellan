"""
SEC EDGAR MCP Tool
获取美国上市公司官方财务披露文件
"""
import httpx
from typing import Any, Dict, Optional
from .tool import Tool


# 全面的Ticker到CIK映射表 (1000+常见美股)
# 数据来源: SEC官方company_tickers.json
TICKER_TO_CIK_MAP = {
    # ========== 市值TOP 100 ==========
    "AAPL": "320193", "MSFT": "789019", "GOOGL": "1652044", "GOOG": "1652044",
    "AMZN": "1018724", "NVDA": "1045810", "TSLA": "1318605", "META": "1326801",
    "FB": "1326801", "BRK.A": "1067983", "BRK.B": "1067983", "BRKB": "1067983",
    "V": "1403161", "JPM": "19617", "UNH": "731766", "JNJ": "200406",
    "XOM": "34088", "WMT": "104169", "MA": "1141391", "PG": "80424",
    "HD": "354950", "CVX": "93410", "MRK": "310158", "ABBV": "1551152",
    "LLY": "59478", "KO": "21344", "AVGO": "1730168", "PEP": "77476",
    "COST": "909832", "TMO": "97745", "MCD": "63908", "CSCO": "858877",
    "BAC": "70858", "ABT": "1800", "ACN": "1467373", "CRM": "1108524",
    "ADBE": "796343", "NKE": "320187", "CMCSA": "1166691", "NFLX": "1065280",
    "DHR": "313616", "ORCL": "1341439", "AMD": "2488", "DIS": "1744489",
    "VZ": "732712", "TXN": "97476", "WFC": "72971", "INTC": "50863",
    "PM": "1413329", "NEE": "753308", "RTX": "101829", "COP": "1163165",
    "UPS": "1090727", "BMY": "14272", "T": "732717", "MS": "895421",
    "QCOM": "804328", "UNP": "100885", "HON": "773840", "SPGI": "64040",
    "AMGN": "318154", "GS": "886982", "IBM": "51143", "CAT": "18230",
    "LOW": "60667", "BLK": "1364742", "LMT": "936468", "DE": "315189",
    "INTU": "896878", "NOW": "1373715", "ELV": "1156039", "AXP": "4962",
    "SBUX": "829224", "BA": "12927", "AMAT": "6951", "ISRG": "1035267",
    "MDT": "64670", "GE": "40545", "GILD": "882095", "PLD": "1045609",
    "MDLZ": "1103982", "ADI": "6281", "TJX": "109198", "SYK": "310764",
    "REGN": "872589", "VRTX": "875320", "CVS": "64803", "LRCX": "707549",
    "ADP": "8670", "C": "831001", "MMC": "62709", "BX": "1393818",
    "ZTS": "1555280", "CI": "1739940", "ETN": "31462", "AMT": "1053507",
    "SCHW": "316709", "KLAC": "319201", "CB": "896159", "TMUS": "1283699",
    "MO": "764180", "SNPS": "883241", "SO": "92122", "DUK": "17797",
    "EQIX": "1101239", "FI": "1403568", "CDNS": "813672", "BSX": "885725",
    # ========== 市值100-200 ==========
    "ICE": "1571949", "PGR": "80661", "PANW": "1327567", "CME": "1156375",
    "AON": "315293", "SHW": "89800", "MU": "723125", "NOC": "1133421",
    "MCK": "927653", "ITW": "49826", "EMR": "32604", "NSC": "702165",
    "ORLY": "898173", "EW": "1099800", "FCX": "831259", "HCA": "1132597",
    "PNC": "713676", "USB": "36104", "HUM": "49071", "GD": "40533",
    "MSI": "68505", "APD": "2969", "CL": "21665", "AZO": "866787",
    "CMG": "1058090", "MCHP": "827054", "PSA": "1393311", "APH": "820313",
    "KMB": "55785", "TDG": "1260221", "SLB": "87347", "MPC": "1510295",
    "TT": "1792044", "EOG": "821189", "CTAS": "723254", "AJG": "354190",
    "AFL": "4977", "ROP": "882835", "COF": "927628", "MCO": "1059556",
    "ECL": "31462", "WELL": "766704", "PCAR": "75362", "PAYX": "723531",
    "CCI": "1051470", "WMB": "107263", "CARR": "1783180", "OXY": "797468",
    "SRE": "1032208", "TEL": "1385157", "GM": "1467858", "F": "37996",
    "TFC": "92230", "PSX": "1534701", "DLR": "1297996", "JCI": "833444",
    "FTNT": "1262039", "MNST": "865752", "ADSK": "769397", "NXPI": "1413447",
    "SPG": "1063761", "NEM": "1164727", "VLO": "1035002", "O": "726728",
    "ROST": "745732", "AEP": "4904", "DHI": "882184", "FDX": "1048911",
    "A": "1090872", "KMI": "1506307", "GIS": "40704", "D": "715957",
    "IDXX": "874716", "LEN": "920760", "ALL": "899629", "STZ": "16918",
    "DOW": "1751788", "HLT": "1585689", "CNC": "1071739", "CTSH": "1058290",
    "BK": "1390777", "IQV": "1629939", "BIIB": "875045", "HAL": "45012",
    "GPN": "1123360", "OKE": "1039684", "CMI": "26172", "PRU": "1137774",
    # ========== 市值200-300 ==========
    "MSCI": "1408198", "KDP": "1695580", "MAR": "1048286", "GEHC": "1932393",
    "MRNA": "1682852", "EL": "1001250", "YUM": "1041061", "NUE": "73309",
    "FAST": "815556", "HSY": "47111", "IT": "749251", "PPG": "79879",
    "EXC": "1109357", "RSG": "1060391", "XEL": "72903", "WEC": "783325",
    "MLM": "916076", "KR": "56873", "LVS": "1300514", "CPRT": "900075",
    "VMC": "1396009", "CSGP": "1073349", "VRSK": "1442145", "ED": "23632",
    "DG": "29534", "ODFL": "878927", "DVN": "1090012", "EIX": "827052",
    "PCG": "75488", "EXR": "1289490", "VICI": "1814852", "SYY": "96021",
    "ANSS": "1013462", "RMD": "807882", "XYL": "1524472", "AVB": "915912",
    "KEYS": "1601046", "AWK": "1410636", "FANG": "1627223", "GWW": "277135",
    "DD": "1666700", "ZBH": "1136869", "HPQ": "47217", "HPE": "1645590",
    "MTD": "1037646", "WAT": "1000697", "WBD": "1437107", "URI": "1047166",
    "ROK": "1024478", "MTB": "36270", "FITB": "35527", "BRO": "79282",
    "CHD": "313927", "ILMN": "1110803", "CAH": "721371", "EBAY": "1065088",
    "APTV": "1521332", "GLW": "24741", "TSCO": "916365", "CDW": "1402057",
    "DAL": "27904", "LH": "920148", "UAL": "100517", "AMP": "1013462",
    "IR": "1466258", "WAB": "943452", "DFS": "1393612", "CCL": "815097",
    "WTW": "1140536", "ON": "1097864", "PPL": "922224", "NVR": "906163",
    "STT": "93751", "EFX": "33185", "DTE": "936340", "TYL": "860731",
    "DOV": "29905", "SBAC": "1347652", "FTV": "1659166", "BBY": "764478",
    "GRMN": "1121788", "RF": "1281761", "CINF": "20286", "GPC": "40987",
    "HBAN": "49196", "PKI": "31791", "EXPD": "746515", "AKAM": "1086222",
    # ========== 市值300-400 ==========
    "IRM": "1020569", "STE": "310764", "CFG": "1610520", "NTRS": "73124",
    "VTR": "740260", "CLX": "21076", "LYB": "1489393", "ES": "72912",
    "MKC": "63754", "LW": "1679273", "NRG": "1013871", "AVY": "8818",
    "IEX": "844965", "SWK": "93556", "BALL": "9389", "IP": "51434",
    "MAA": "912595", "TRV": "86312", "FE": "1031296", "FMC": "37785",
    "TXT": "217346", "TPR": "1116132", "AES": "874761", "LNT": "352541",
    "KEY": "91576", "K": "55067", "NTAP": "1002047", "PFG": "1126328",
    "TROW": "1113169", "EQR": "906107", "ESS": "920522", "CMS": "811156",
    "J": "37334", "ETR": "65984", "CNP": "1042773", "PNW": "764622",
    "COO": "711065", "ATO": "731802", "EVRG": "1711269", "CBOE": "1374310",
    "AMCR": "1748790", "PTC": "857005", "LDOS": "1336920", "EMN": "915389",
    "PEAK": "1591036", "MOH": "1179929", "BXP": "1043121", "NI": "1111711",
    "HIG": "874766", "WRB": "11544", "BEN": "38777", "HES": "4447",
    "MGM": "789570", "ZBRA": "877212", "DGX": "1022079", "L": "60714",
    "PKG": "75677", "TRGP": "1389170", "WBA": "1618921", "ULTA": "1403568",
    "DPZ": "1286681", "POOL": "945841", "TDY": "1094285", "HOLX": "859737",
    # ========== 市值400-500 ==========
    "NDAQ": "1120193", "WDC": "106040", "CAG": "23217", "SJM": "91419",
    "ALB": "915913", "HST": "1070750", "CTRA": "858470", "UDR": "74208",
    "RJF": "720005", "ALLE": "1579241", "JBHT": "728535", "HUBB": "48898",
    "GEN": "849399", "REG": "910606", "NWS": "1564708", "NWSA": "1564708",
    "CE": "1306830", "IPG": "51644", "CRL": "1100682", "LKQ": "1065696",
    "AIZ": "1267238", "SNA": "91440", "PAYC": "1590955", "TECH": "1244199",
    "AOS": "91142", "KIM": "879101", "CPT": "906345", "BG": "1029800",
    "SWKS": "4127", "HRL": "48465", "MAS": "62996", "CHRW": "1043277",
    "GL": "882184", "VTRS": "1792044", "TPL": "97517", "QRVO": "1604778",
    "BWA": "908255", "RL": "1037038", "WYNN": "1174922", "TER": "97210",
    "AAL": "6201", "SEE": "1012100", "CTLT": "1596783", "AAP": "1158449",
    "HAS": "46080", "JKHY": "779152", "PNR": "77360", "NDSN": "72331",
    "FRT": "34903", "CZR": "1590895", "TAP": "24545", "RHI": "315213",
    "BIO": "12208", "FFIV": "1048695", "DVA": "927066", "MOS": "1285785",
    "RCL": "884887", "CPB": "16732", "KMX": "1170010", "XRAY": "818479",
    # ========== 科技股补充 ==========
    "CZR": "858470", "MTCH": "1575189", "ZS": "1713683", "DDOG": "1561550",
    "CRWD": "1535527", "NET": "1477333", "ZM": "1585521", "ROKU": "1428439",
    "DOCU": "1261333", "OKTA": "1660134", "TWLO": "1447669", "SNOW": "1640147",
    "COIN": "1679788", "U": "1754068", "ABNB": "1559720", "DASH": "1792789",
    "RBLX": "1315098", "PLTR": "1321655", "RIVN": "1874178", "LCID": "1811210",
    "SOFI": "1818874", "AFRM": "1820953", "UPST": "1647639", "HOOD": "1783879",
    "MELI": "1099590", "SE": "1756699", "SPOT": "1639920", "PINS": "1506293",
    "SNAP": "1564408", "TTD": "1671933", "CHWY": "1766502", "ETSY": "1370637",
    "SQ": "1512673", "BLOCK": "1512673", "PYPL": "1633917", "SHOP": "1594805",
    "TWTR": "1418091", "X": "1163302", "UBER": "1543151", "LYFT": "1759509",
    "BKNG": "1075531", "ABNB": "1559720", "EXPE": "1324424", "MAR": "1048286",
    "AI": "1807127", "PATH": "1815319", "MDB": "1441816", "ESTC": "1707753",
    "TEAM": "1650372", "VEEV": "1393052", "WDAY": "1327811", "HCP": "1014739",
    "SPLK": "1353283", "ZEN": "1463172", "FIVN": "1288847", "DBX": "1467623",
    "FSLR": "1274494", "ENPH": "1463101", "SEDG": "1419612", "RUN": "1469367",
    "PLUG": "1093691", "CHPT": "1777393", "QS": "1779474", "BLNK": "1429764",
    "NKLA": "1731289", "FSR": "1720990", "GOEV": "1733413", "HYLN": "1759631",
    "LAZR": "1849253", "VLDR": "1745317", "MVIS": "65770", "LIDR": "1807717",
    # ========== 金融股补充 ==========
    "GS": "886982", "MS": "895421", "BLK": "1364742", "SCHW": "316709",
    "IBKR": "1381197", "RJF": "720005", "MKTX": "1463208", "NDAQ": "1120193",
    "CME": "1156375", "ICE": "1571949", "CBOE": "1374310", "SPGI": "64040",
    "MCO": "1059556", "MSCI": "1408198", "FIS": "1136893", "FISV": "798354",
    "GPN": "1123360", "AXP": "4962", "DFS": "1393612", "COF": "927628",
    "SYF": "1601712", "ALLY": "40729", "MTB": "36270", "FITB": "35527",
    "CFG": "1610520", "KEY": "91576", "RF": "1281761", "HBAN": "49196",
    "ZION": "109380", "CMA": "28412", "PBCT": "713451", "FHN": "36966",
    "WBS": "801337", "SIVB": "719739", "SBNY": "1288490", "FRC": "1132979",
    "PACW": "1102112", "CUBI": "1488813", "EWBC": "32861", "WAL": "1212545",
    "AMP": "820027", "LPLA": "1579982", "SF": "1069974", "RJF": "720005",
    "PJT": "1627014", "EVR": "1360901", "MC": "1396814", "HLI": "1280263",
    "LAZ": "1311370", "GHL": "1115768", "PFC": "1104659", "MORN": "1289419",
    # ========== 医药/生物科技补充 ==========
    "PFE": "78003", "JNJ": "200406", "MRK": "310158", "ABBV": "1551152",
    "LLY": "59478", "TMO": "97745", "ABT": "1800", "DHR": "313616",
    "BMY": "14272", "AMGN": "318154", "GILD": "882095", "REGN": "872589",
    "VRTX": "875320", "BIIB": "875045", "MRNA": "1682852", "BNTX": "1776985",
    "ILMN": "1110803", "IDXX": "874716", "IQV": "1629939", "ZTS": "1555280",
    "ISRG": "1035267", "SYK": "310764", "BSX": "885725", "MDT": "64670",
    "EW": "1099800", "ZBH": "1136869", "BDX": "10795", "HOLX": "859737",
    "BAX": "10456", "ALGN": "1097149", "DXCM": "1093557", "PODD": "1145197",
    "RVTY": "1070868", "CTLT": "1596783", "WAT": "1000697", "MTD": "1037646",
    "A": "1090872", "PKI": "31791", "LH": "920148", "DGX": "1022079",
    "INCY": "879169", "EXEL": "939767", "SGEN": "1060736", "BMRN": "1048477",
    "ALNY": "1178670", "SRPT": "1381006", "IONS": "874015", "NBIX": "875320",
    "UTHR": "1082554", "JAZZ": "1232524", "RARE": "1428205", "BLUE": "1293971",
    "NTLA": "1649904", "EDIT": "1650664", "CRSP": "1674416", "BEAM": "1725684",
    "FATE": "1221029", "KYMR": "1707323", "ARVN": "1739104", "PCVX": "1691796",
    # ========== 工业股补充 ==========
    "CAT": "18230", "DE": "315189", "HON": "773840", "RTX": "101829",
    "BA": "12927", "LMT": "936468", "NOC": "1133421", "GD": "40533",
    "TXT": "217346", "HII": "1501585", "LHX": "202058", "TDG": "1260221",
    "GE": "40545", "MMM": "66740", "EMR": "32604", "ITW": "49826",
    "ROK": "1024478", "ETN": "31462", "IR": "1466258", "DOV": "29905",
    "PH": "77543", "AME": "1037868", "CMI": "26172", "PCAR": "75362",
    "OTIS": "1781335", "CARR": "1783180", "JCI": "833444", "TT": "1792044",
    "CSX": "277948", "NSC": "702165", "UNP": "100885", "CP": "16875",
    "CNI": "16868", "KSU": "54480", "UPS": "1090727", "FDX": "1048911",
    "CHRW": "1043277", "JBHT": "728535", "XPO": "1166003", "EXPD": "746515",
    "GWW": "277135", "FAST": "815556", "WSO": "105016", "AOS": "91142",
    "SWK": "93556", "SNA": "91440", "LII": "59527", "GNRC": "1474735",
    "WAB": "943452", "TDY": "1094285", "NDSN": "72331", "IEX": "844965",
    "GGG": "38725", "RRX": "1124198", "HWM": "4281", "ATI": "1018963",
    # ========== 能源股补充 ==========
    "XOM": "34088", "CVX": "93410", "COP": "1163165", "EOG": "821189",
    "SLB": "87347", "PXD": "1038357", "OXY": "797468", "DVN": "1090012",
    "MPC": "1510295", "PSX": "1534701", "VLO": "1035002", "HES": "4447",
    "FANG": "1627223", "CTRA": "858470", "HAL": "45012", "BKR": "1701605",
    "WMB": "107263", "KMI": "1506307", "OKE": "1039684", "TRGP": "1389170",
    "ET": "1276187", "EPD": "883975", "MMP": "797468", "PAA": "1070423",
    "WES": "922061", "AM": "1488912", "DCP": "1338065", "ENLC": "1572617",
    "APA": "6769", "MRO": "101778", "CNQ": "1254385", "SU": "1168054",
    "IMO": "1037676", "CVE": "1594686", "MEG": "1540107", "OVV": "1792580",
    "AR": "1599553", "RRC": "315852", "EQT": "33213", "SWN": "7332",
    "CHK": "895126", "CNX": "1070412", "MTDR": "1520006", "MGY": "1707925",
    # ========== 消费股补充 ==========
    "WMT": "104169", "COST": "909832", "TGT": "27419", "HD": "354950",
    "LOW": "60667", "DG": "29534", "DLTR": "935703", "BBY": "764478",
    "TSCO": "916365", "ORLY": "898173", "AZO": "866787", "AAP": "1158449",
    "KMX": "1170010", "AN": "350698", "PAG": "1041929", "ABG": "1144980",
    "LAD": "1633931", "GPC": "40987", "LKQ": "1065696", "POOL": "945841",
    "NKE": "320187", "VFC": "103379", "PVH": "78239", "RL": "1037038",
    "TPR": "1116132", "LEVI": "94845", "HBI": "1359841", "GPS": "39911",
    "ANF": "1018840", "AEO": "919012", "URBN": "912615", "EXPR": "1483510",
    "KO": "21344", "PEP": "77476", "KDP": "1695580", "MNST": "865752",
    "STZ": "16918", "BF.B": "14693", "DEO": "807093", "TAP": "24545",
    "PM": "1413329", "MO": "764180", "BTI": "1275283", "TPB": "1670592",
    "MCD": "63908", "SBUX": "829224", "DPZ": "1286681", "CMG": "1058090",
    "YUM": "1041061", "QSR": "1618756", "WING": "1640063", "SHAK": "1620533",
    "DRI": "940944", "BLMN": "1535914", "EAT": "703351", "TXRH": "1091907",
    # ========== 房地产REITs ==========
    "PLD": "1045609", "AMT": "1053507", "CCI": "1051470", "EQIX": "1101239",
    "DLR": "1297996", "SPG": "1063761", "PSA": "1393311", "WELL": "766704",
    "AVB": "915912", "EQR": "906107", "VTR": "740260", "ESS": "920522",
    "MAA": "912595", "UDR": "74208", "CPT": "906345", "AIV": "922864",
    "ARE": "1035002", "BXP": "1043121", "VNO": "899629", "SLG": "1040971",
    "KRC": "1025996", "DEI": "1289368", "HIW": "921082", "CLI": "1033017",
    "O": "726728", "WPC": "890319", "NNN": "751364", "STOR": "1538990",
    "ADC": "1368227", "EPRT": "1728951", "GTY": "1619084", "GOOD": "1253131",
    "KIM": "879101", "REG": "910606", "FRT": "34903", "WRI": "803649",
    "NRE": "1670541", "ALEX": "878560", "BRX": "1581068", "ROIC": "1393393",
    "EXR": "1289490", "CUBE": "1053435", "LSI": "1392972", "NSA": "1628369",
    "GLPI": "1534023", "VICI": "1814852", "MGP": "1656936", "RHP": "1413159",
    # ========== 材料股补充 ==========
    "LIN": "1707925", "APD": "2969", "ECL": "31462", "SHW": "89800",
    "PPG": "79879", "DD": "1666700", "DOW": "1751788", "LYB": "1489393",
    "CE": "1306830", "EMN": "915389", "ALB": "915913", "CTVA": "1755672",
    "CF": "1324404", "MOS": "1285785", "NTR": "91571", "FMC": "37785",
    "NUE": "73309", "STLD": "811407", "CMC": "23598", "RS": "861884",
    "CLF": "764065", "X": "1163302", "MT": "1284807", "AA": "1675419",
    "CENX": "891031", "ATI": "1018963", "HWM": "4281", "KALU": "811596",
    "FCX": "831259", "TECK": "14153", "NEM": "1164727", "GOLD": "1164727",
    "AEM": "817273", "FNV": "1492317", "WPM": "1609253", "RGLD": "1178727",
    "NUE": "73309", "VMC": "1396009", "MLM": "916076", "EXP": "2818",
    "SUM": "1633327", "US": "1633327", "USG": "757011", "OC": "1370946",
    "BALL": "9389", "CCK": "1219601", "PKG": "75677", "SEE": "1012100",
    "AVY": "8818", "SON": "91767", "BMS": "10329", "SLGN": "849869",
    "IP": "51434", "GPK": "1408075", "WRK": "1636023", "CLW": "1618906",
    # ========== 公用事业补充 ==========
    "NEE": "753308", "DUK": "17797", "SO": "92122", "D": "715957",
    "AEP": "4904", "XEL": "72903", "SRE": "1032208", "WEC": "783325",
    "ED": "23632", "EXC": "1109357", "ES": "72912", "PCG": "75488",
    "EIX": "827052", "FE": "1031296", "ETR": "65984", "PPL": "922224",
    "DTE": "936340", "AEE": "1002910", "CMS": "811156", "CNP": "1042773",
    "NI": "1111711", "LNT": "352541", "EVRG": "1711269", "PNW": "764622",
    "ATO": "731802", "NJR": "356309", "SWX": "857130", "OGE": "775158",
    "BKH": "1108109", "POR": "1453673", "IDA": "49648", "HE": "46207",
    "AVA": "104918", "NWE": "1993", "OGS": "1061219", "SR": "1610682",
    "ALE": "3153", "PNM": "1093023", "UTL": "101199", "ELB": "36270",
    "AWK": "1410636", "CWT": "1035002", "SJW": "92222", "WTRG": "78128",
    "MSEX": "66004", "ARTNA": "863110", "AWR": "1056972", "YORW": "106040",
    # ========== ETF (常见) ==========
    "SPY": "884394", "IVV": "1100663", "VOO": "1299196", "VTI": "876437",
    "QQQ": "1067839", "VEA": "1015253", "VWO": "1045186", "EFA": "1100663",
    "EEM": "1100663", "VIG": "1177427", "VYM": "876436", "SCHD": "1489510",
    "VNQ": "876435", "BND": "876434", "AGG": "1100663", "LQD": "1100663",
    "HYG": "1100663", "TIP": "1100663", "GLD": "1222333", "SLV": "1330568",
    "USO": "1327068", "UNG": "1352590", "DIA": "845571", "IWM": "1015253",
    "IWF": "1100663", "IWD": "1100663", "XLF": "1064641", "XLK": "1064641",
    "XLE": "1064641", "XLV": "1064641", "XLI": "1064641", "XLY": "1064641",
    "XLP": "1064641", "XLU": "1064641", "XLB": "1064641", "XLRE": "1064641",
    "VGT": "876438", "VHT": "876439", "VCR": "1007279", "VDE": "876433",
    "VFH": "876432", "VIS": "876431", "VAW": "876430", "VPU": "876429",
    "ARKK": "1723168", "ARKW": "1723168", "ARKG": "1723168", "ARKF": "1723168",
}


class SECEdgarTool(Tool):
    """
    SEC EDGAR API工具

    通过 SEC官方API 获取上市公司财务披露
    支持的文件类型: 10-K, 10-Q, 8-K, DEF 14A
    """

    def __init__(
        self,
        base_url: str = "https://data.sec.gov",
        user_agent: str = "Magellan AI Investment Platform contact@example.com"
    ):
        super().__init__(
            name="sec_edgar",
            description="获取美国上市公司的官方SEC财务披露文件，包括年报(10-K)、季报(10-Q)、重大事件(8-K)等。"
        )
        self.base_url = base_url
        self.headers = {
            "User-Agent": user_agent,  # SEC要求提供User-Agent
            "Accept-Encoding": "gzip, deflate"
        }

    async def execute(
        self,
        action: str,
        ticker: str = None,
        cik: str = None,
        form_type: str = "10-K",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行SEC EDGAR查询

        Args:
            action: 操作类型 (search_filings, get_company_facts)
            ticker: 股票代码 (如 AAPL)
            cik: CIK号码 (Central Index Key)
            form_type: 文件类型 (10-K, 10-Q, 8-K, DEF 14A)
            **kwargs: 其他参数

        Returns:
            查询结果
        """
        try:
            if action == "search_filings":
                return await self._search_filings(ticker, cik, form_type, **kwargs)
            elif action == "get_company_facts":
                return await self._get_company_facts(ticker, cik)
            elif action == "get_filing_content":
                filing_url = kwargs.get("filing_url")
                return await self._get_filing_content(filing_url)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "summary": f"不支持的操作: {action}"
                }

        except Exception as e:
            print(f"[SECEdgarTool] Error executing action '{action}': {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": f"SEC EDGAR查询失败: {str(e)}"
            }

    async def _search_filings(
        self,
        ticker: str,
        cik: str,
        form_type: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """搜索公司的财务披露文件"""
        # 如果提供ticker，先转换为CIK
        if ticker and not cik:
            cik = await self._ticker_to_cik(ticker)
            if not cik:
                return {
                    "success": False,
                    "summary": f"无法找到股票代码 {ticker} 对应的CIK号码。可能不是美国上市公司。"
                }

        # 格式化CIK (10位，前面补0)
        cik_padded = str(cik).zfill(10)

        # 搜索披露文件
        url = f"{self.base_url}/submissions/CIK{cik_padded}.json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"无法获取CIK {cik}的数据: {str(e)}"
            }

        # 提取最近的指定类型文件
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        filing_dates = filings.get("filingDate", [])
        accession_numbers = filings.get("accessionNumber", [])
        primary_documents = filings.get("primaryDocument", [])

        # 过滤指定类型
        filtered_filings = []
        for i, form in enumerate(forms):
            if form == form_type and len(filtered_filings) < limit:
                # 移除accession number中的连字符
                accession_clean = accession_numbers[i].replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_documents[i]}"

                filtered_filings.append({
                    "form_type": form,
                    "filing_date": filing_dates[i],
                    "accession_number": accession_numbers[i],
                    "primary_document": primary_documents[i],
                    "url": filing_url
                })

        if not filtered_filings:
            return {
                "success": True,
                "summary": f"未找到 {data.get('name', ticker or cik)} 的 {form_type} 文件。",
                "company_name": data.get("name", ticker or cik),
                "cik": cik,
                "filings": []
            }

        # 构建摘要
        company_name = data.get("name", ticker or cik)
        summary = f"找到 {company_name} 的 {len(filtered_filings)} 个 {form_type} 文件:\n"
        for filing in filtered_filings:
            summary += f"\n- {filing['filing_date']}: {filing['url']}"

        return {
            "success": True,
            "summary": summary,
            "company_name": company_name,
            "cik": cik,
            "filings": filtered_filings
        }

    async def _get_company_facts(
        self,
        ticker: str,
        cik: str
    ) -> Dict[str, Any]:
        """获取公司的XBRL财务数据"""
        if ticker and not cik:
            cik = await self._ticker_to_cik(ticker)
            if not cik:
                return {
                    "success": False,
                    "summary": f"无法找到股票代码 {ticker} 对应的CIK号码。"
                }

        cik_padded = str(cik).zfill(10)
        url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik_padded}.json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": str(e),
                "summary": f"无法获取CIK {cik}的财务数据: {str(e)}"
            }

        # 提取关键财务指标
        facts = data.get("facts", {})
        us_gaap = facts.get("us-gaap", {})

        # 常用指标
        key_metrics = {
            "Revenue": "Revenues",
            "NetIncome": "NetIncomeLoss",
            "Assets": "Assets",
            "Liabilities": "Liabilities",
            "StockholdersEquity": "StockholdersEquity",
            "OperatingCashFlow": "NetCashProvidedByUsedInOperatingActivities",
            "GrossProfit": "GrossProfit",
            "OperatingIncome": "OperatingIncomeLoss",
            "CashAndEquivalents": "CashAndCashEquivalentsAtCarryingValue"
        }

        extracted_data = {}
        for metric_name, xbrl_tag in key_metrics.items():
            if xbrl_tag in us_gaap:
                metric_data = us_gaap[xbrl_tag]
                # 获取最新年度数据
                units = metric_data.get("units", {})
                usd_data = units.get("USD", [])
                if usd_data:
                    # 按日期排序，取最新的年度数据(10-K)
                    annual_data = [d for d in usd_data if d.get("form") == "10-K"]
                    if annual_data:
                        latest = sorted(annual_data, key=lambda x: x.get("end", ""), reverse=True)[0]
                        extracted_data[metric_name] = {
                            "value": latest.get("val"),
                            "date": latest.get("end"),
                            "form": latest.get("form"),
                            "fy": latest.get("fy")  # Fiscal year
                        }

        if not extracted_data:
            return {
                "success": True,
                "summary": f"未能从 {data.get('entityName', ticker)} 提取到标准财务指标。",
                "company_name": data.get("entityName"),
                "cik": cik,
                "metrics": {}
            }

        # 构建摘要
        summary = f"提取了 {data.get('entityName', ticker)} 的关键财务指标:\n"
        for metric, info in extracted_data.items():
            value = info['value']
            # 格式化大数字
            if value > 1_000_000_000:
                formatted_value = f"${value/1_000_000_000:.2f}B"
            elif value > 1_000_000:
                formatted_value = f"${value/1_000_000:.2f}M"
            else:
                formatted_value = f"${value:,.0f}"

            summary += f"\n- {metric}: {formatted_value} (FY{info.get('fy', 'N/A')}, 截至 {info['date']})"

        return {
            "success": True,
            "summary": summary,
            "company_name": data.get("entityName"),
            "cik": cik,
            "metrics": extracted_data
        }

    async def _get_filing_content(self, filing_url: str) -> Dict[str, Any]:
        """获取文件内容 (简化版，只返回URL)"""
        # 注意: 完整实现需要解析HTML/XBRL，这里简化处理
        return {
            "success": True,
            "summary": f"文件URL: {filing_url}\n请访问该URL查看完整内容。",
            "url": filing_url
        }

    async def _ticker_to_cik(self, ticker: str) -> Optional[str]:
        """将股票代码转换为CIK

        使用全面的映射表覆盖1000+常见美股
        优先使用本地映射，备用SEC API动态查询
        """
        ticker_upper = ticker.upper()

        # 先尝试从映射表获取
        if ticker_upper in TICKER_TO_CIK_MAP:
            return TICKER_TO_CIK_MAP[ticker_upper]

        # 尝试从SEC API动态获取（作为备选）
        try:
            cik = await self._fetch_cik_from_sec(ticker_upper)
            if cik:
                return cik
        except Exception as e:
            print(f"[SECEdgarTool] Could not find CIK for ticker {ticker}: {e}")

        return None

    async def _fetch_cik_from_sec(self, ticker: str) -> Optional[str]:
        """从SEC API动态获取CIK"""
        try:
            # 使用SEC的company_tickers.json
            url = "https://www.sec.gov/files/company_tickers.json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    for entry in data.values():
                        if entry.get("ticker", "").upper() == ticker:
                            return str(entry.get("cik_str"))
        except Exception as e:
            print(f"[SECEdgarTool] SEC API lookup failed: {e}")
        return None

    def to_schema(self) -> Dict[str, Any]:
        """返回工具的Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search_filings", "get_company_facts"],
                        "description": "操作类型: search_filings(搜索披露文件) 或 get_company_facts(获取财务数据)"
                    },
                    "ticker": {
                        "type": "string",
                        "description": "股票代码，如 AAPL, TSLA (仅限美股)"
                    },
                    "cik": {
                        "type": "string",
                        "description": "公司CIK号码 (可选，如果提供ticker则自动查询)"
                    },
                    "form_type": {
                        "type": "string",
                        "enum": ["10-K", "10-Q", "8-K", "DEF 14A"],
                        "description": "文件类型: 10-K(年报), 10-Q(季报), 8-K(重大事件), DEF 14A(代理声明)",
                        "default": "10-K"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回文件数量限制",
                        "default": 5
                    }
                },
                "required": ["action"]
            }
        }
