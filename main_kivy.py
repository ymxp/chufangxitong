import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.properties import BooleanProperty, ListProperty, StringProperty, ObjectProperty
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle
import sqlite3
import datetime
import os
import sys
import re

# 数据库操作类
class DatabaseManager:
    def __init__(self):
        # 获取应用程序运行目录
        if getattr(sys, 'frozen', False):
            # 打包后的EXE运行
            base_dir = os.path.dirname(sys.executable)
        else:
            # 直接Python运行
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 使用绝对路径连接数据库
        db_path = os.path.join(base_dir, 'zhongyi.db')
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # 创建患者表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            age INTEGER NOT NULL,
            address TEXT,
            phone TEXT
        )''')
        
        # 创建药品表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT NOT NULL,
            price REAL NOT NULL,
            sale_price REAL NOT NULL,
            pinyin TEXT
        )''')
        
        # 检查并添加售价字段（如果不存在）
        self.cursor.execute("PRAGMA table_info(medicines)")
        medicine_columns = [column[1] for column in self.cursor.fetchall()]
        if 'sale_price' not in medicine_columns:
            self.cursor.execute("ALTER TABLE medicines ADD COLUMN sale_price REAL NOT NULL DEFAULT 0")
        
        # 检查并添加首字母缩写字段（如果不存在）
        if 'pinyin' not in medicine_columns:
            self.cursor.execute("ALTER TABLE medicines ADD COLUMN pinyin TEXT")
        
        # 创建处方表（如果不存在）
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            diagnosis TEXT,
            date TEXT NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )''')
        
        # 检查并添加新字段
        self.cursor.execute("PRAGMA table_info(prescriptions)")
        columns = [column[1] for column in self.cursor.fetchall()]
        
        # 添加缺失的字段
        if 'chief_complaint' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN chief_complaint TEXT")
        if 'present_illness' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN present_illness TEXT")
        if 'past_history' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN past_history TEXT")
        if 'allergy_history' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN allergy_history TEXT")
        # 添加药剂信息字段
        if 'decoct' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN decoct INTEGER DEFAULT 0")
        if 'external' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN external INTEGER DEFAULT 0")
        if 'hospital' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN hospital INTEGER DEFAULT 0")
        if 'payment' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN payment TEXT DEFAULT '自费'")
        if 'medicine_count' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN medicine_count INTEGER DEFAULT 7")
        if 'dosage_form' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN dosage_form TEXT DEFAULT '免煎'")
        if 'frequency' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN frequency TEXT DEFAULT '一次'")
        if 'usage' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN usage TEXT DEFAULT '水煎服,1日1剂,1日2次'")
        if 'requirements' not in columns:
            self.cursor.execute("ALTER TABLE prescriptions ADD COLUMN requirements TEXT")
        
        # 创建处方药品表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescription_medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prescription_id INTEGER NOT NULL,
            medicine_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            FOREIGN KEY (prescription_id) REFERENCES prescriptions (id),
            FOREIGN KEY (medicine_id) REFERENCES medicines (id)
        )''')
        
        # 创建设置表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL
        )''')
        
        # 创建方剂模板表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS formulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            ingredients TEXT NOT NULL
        )''')
        
        # 插入默认设置
        default_settings = [
            ("font_size", "10"),
            ("font_family", "SimHei"),
            ("language", "zh_CN"),
            ("username", "admin"),
            ("password", "123456")
        ]
        
        for key, value in default_settings:
            self.cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
            ''', (key, value))
        
        # 插入默认方剂模板（伤寒论方剂）
        self.cursor.execute("SELECT COUNT(*) FROM formulas")
        if self.cursor.fetchone()[0] == 0:
            default_formulas = [
                ("麻黄汤", "发汗解表，宣肺平喘", "麻黄10g,桂枝6g,杏仁9g,甘草3g"),
                ("桂枝汤", "解肌发表，调和营卫", "桂枝9g,芍药9g,甘草6g,生姜9g,大枣12枚"),
                ("葛根汤", "发汗解表，升津舒筋", "葛根12g,麻黄9g,桂枝6g,生姜9g,甘草6g,芍药6g,大枣12枚"),
                ("小青龙汤", "解表散寒，温肺化饮", "麻黄9g,芍药9g,细辛3g,干姜6g,甘草6g,桂枝9g,五味子6g,半夏9g"),
                ("大青龙汤", "发汗解表，清热除烦", "麻黄12g,桂枝6g,甘草6g,杏仁9g,石膏18g,生姜9g,大枣12枚"),
                ("麻杏甘石汤", "辛凉宣泄，清肺平喘", "麻黄9g,杏仁9g,甘草6g,石膏18g"),
                ("白虎汤", "清热生津", "石膏30g,知母12g,甘草6g,粳米12g"),
                ("小柴胡汤", "和解少阳", "柴胡24g,黄芩9g,人参9g,甘草6g,半夏9g,生姜9g,大枣12枚"),
                ("大柴胡汤", "和解少阳，内泻热结", "柴胡12g,黄芩9g,芍药9g,半夏9g,生姜15g,枳实9g,大枣12枚,大黄6g"),
                ("四逆汤", "回阳救逆", "附子15g,干姜9g,甘草6g"),
                ("理中汤", "温中散寒，补气健脾", "人参9g,干姜9g,白术9g,甘草9g"),
                ("真武汤", "温阳利水", "茯苓9g,芍药9g,生姜9g,白术6g,附子9g"),
                ("五苓散", "利水渗湿，温阳化气", "猪苓9g,泽泻15g,白术9g,茯苓9g,桂枝6g"),
                ("茵陈蒿汤", "清热利湿退黄", "茵陈18g,栀子12g,大黄6g"),
                ("麻黄连翘赤小豆汤", "解表散邪，清热利湿", "麻黄6g,连翘9g,杏仁6g,赤小豆30g,大枣12枚,生梓白皮15g,生姜6g,甘草6g"),
                ("桂枝茯苓丸", "活血化瘀，缓消癥块", "桂枝9g,茯苓9g,牡丹皮9g,桃仁9g,芍药9g"),
                ("桃核承气汤", "破血下瘀", "桃仁12g,大黄12g,桂枝6g,甘草6g,芒硝6g"),
                ("抵挡汤", "破血逐瘀", "水蛭6g,虻虫6g,桃仁9g,大黄9g"),
                ("小建中汤", "温中补虚，和里缓急", "桂枝9g,芍药18g,甘草6g,生姜9g,大枣12枚,饴糖30g"),
                ("炙甘草汤", "滋阴养血，益气温阳，复脉定悸", "炙甘草12g,生姜9g,桂枝9g,人参6g,生地黄30g,阿胶6g,麦门冬10g,麻仁10g,大枣10枚")
            ]
            
            self.cursor.executemany('''
            INSERT INTO formulas (name, description, ingredients) VALUES (?, ?, ?)
            ''', default_formulas)
            self.conn.commit()
        
        # 插入一些默认药品
        default_medicines = [
            ("麻黄", "g", 0.10, 0.15),
            ("桂枝", "g", 0.12, 0.18),
            ("甘草", "g", 0.08, 0.12),
            ("杏仁", "g", 0.15, 0.22),
            ("石膏", "g", 0.05, 0.08),
            ("知母", "g", 0.18, 0.27),
            ("黄芩", "g", 0.16, 0.24),
            ("黄连", "g", 0.25, 0.38),
            ("黄柏", "g", 0.14, 0.21),
            ("栀子", "g", 0.12, 0.18)
        ]
        
        self.cursor.execute("SELECT COUNT(*) FROM medicines")
        if self.cursor.fetchone()[0] == 0:
            # 生成首字母缩写并插入默认药品
            medicines_with_pinyin = []
            for medicine in default_medicines:
                name, unit, price, sale_price = medicine
                pinyin = get_pinyin_initial(name)
                medicines_with_pinyin.append((name, unit, price, sale_price, pinyin))
            
            self.cursor.executemany('''
            INSERT INTO medicines (name, unit, price, sale_price, pinyin) VALUES (?, ?, ?, ?, ?)
            ''', medicines_with_pinyin)
        else:
            # 为现有药品生成首字母缩写
            self.cursor.execute("SELECT id, name FROM medicines WHERE pinyin IS NULL OR pinyin = ''")
            medicines_to_update = self.cursor.fetchall()
            for medicine_id, name in medicines_to_update:
                pinyin = get_pinyin_initial(name)
                self.cursor.execute("UPDATE medicines SET pinyin = ? WHERE id = ?", (pinyin, medicine_id))
        
        self.conn.commit()
    
    def close(self):
        self.conn.close()

# 汉字转首字母缩写的函数
def get_pinyin_initial(name):
    # 汉字首字母映射表
    pinyin_map = {
        # 基本汉字
        '一': 'Y', '丁': 'D', '七': 'Q', '十': 'S', '厂': 'C', '万': 'W', '丈': 'Z', '三': 'S', '上': 'S', '下': 'X', 
        '不': 'B', '与': 'Y', '丐': 'G', '丑': 'C', '专': 'Z', '且': 'Q', '丕': 'P', '世': 'S', '丘': 'Q', '丙': 'B', 
        '业': 'Y', '东': 'D', '丝': 'S', '丞': 'C', '两': 'L', '严': 'Y', '并': 'B', '丧': 'S', '丸': 'W', '丹': 'D', 
        '为': 'W', '主': 'Z', '丽': 'L', '举': 'J', '义': 'Y', '之': 'Z', '乌': 'W', '乎': 'H', '乍': 'Z', '乏': 'F', 
        '乐': 'L', '乒': 'P', '乓': 'P', '乔': 'Q', '乖': 'G', '乘': 'C', '乙': 'Y', '九': 'J', '乞': 'Q', '也': 'Y', 
        '习': 'X', '乡': 'X', '书': 'S', '买': 'M', '乱': 'L', '乳': 'R', '乾': 'Q', '予': 'Y', '争': 'Z', '于': 'Y', 
        '亏': 'K', '云': 'Y', '互': 'H', '五': 'W', '井': 'J', '亘': 'G', '亚': 'Y', '些': 'X', '亟': 'J', '亡': 'W', 
        '亢': 'K', '交': 'J', '亥': 'H', '亦': 'Y', '产': 'C', '亨': 'H', '亩': 'M', '享': 'X', '京': 'J', '亭': 'T', 
        '亮': 'L', '亲': 'Q', '亳': 'B', '亵': 'X', '人': 'R', '儿': 'E', '入': 'R', '八': 'B', '仑': 'L', '仓': 'C', 
        '仔': 'Z', '仕': 'S', '他': 'T', '仗': 'Z', '付': 'F', '仙': 'X', '仟': 'Q', '仪': 'Y', '仲': 'Z', '任': 'R', 
        '份': 'F', '仿': 'F', '伉': 'K', '伪': 'W', '伊': 'Y', '何': 'H', '伟': 'W', '俐': 'L', '俏': 'Q', '侮': 'W', 
        '侯': 'H', '侉': 'K', '侣': 'L', '侗': 'D', '侃': 'K', '侏': 'Z', '佻': 'T', '佼': 'J', '侪': 'C', '侬': 'N', 
        '促': 'C', '俄': 'E', '俅': 'Q', '俊': 'J', '刀': 'D', '刁': 'D', '刃': 'R', '分': 'F', '切': 'Q', '刊': 'K', 
        '刎': 'W', '刑': 'X', '划': 'H', '列': 'L', '则': 'Z', '刚': 'G', '创': 'C', '判': 'P', '利': 'L', '别': 'B', 
        '刮': 'G', '到': 'D', '制': 'Z', '刷': 'S', '券': 'Q', '刹': 'S', '刺': 'C', '刻': 'K', '剃': 'T', '削': 'X', 
        '剑': 'J', '剔': 'T', '剖': 'P', '力': 'L', '勺': 'S', '匀': 'Y', '勿': 'W', '勾': 'G', '匆': 'C', '匍': 'P', 
        '匕': 'B', '化': 'H', '北': 'B', '匙': 'C', '匝': 'Z', '匡': 'K', '匠': 'J', '匣': 'X', '医': 'Y', '区': 'Q', 
        '匹': 'P', '卜': 'B', '又': 'Y', '口': 'K', '土': 'T', '士': 'S', '夕': 'X', '大': 'D', '女': 'N', '子': 'Z', 
        '宀': 'M', '寸': 'C', '小': 'X', '尸': 'S', '山': 'S', '川': 'C', '工': 'G', '己': 'J', '巾': 'J', '干': 'G', 
        '幺': 'Y', '广': 'G', '弋': 'Y', '弓': 'G', '彡': 'X', '彳': 'C', '心': 'X', '戈': 'G', '户': 'H', '手': 'S', 
        '支': 'Z', '文': 'W', '斗': 'D', '斤': 'J', '方': 'F', '无': 'W', '日': 'R', '月': 'Y', '木': 'M', '欠': 'Q', 
        '止': 'Z', '歹': 'D', '毛': 'M', '氏': 'S', '气': 'Q', '水': 'S', '火': 'H', '爪': 'Z', '父': 'F', '片': 'P', 
        '牙': 'Y', '牛': 'N', '犬': 'Q', '玄': 'X', '玉': 'Y', '瓜': 'G', '瓦': 'W', '甘': 'G', '生': 'S', '用': 'Y', 
        '田': 'T', '白': 'B', '皮': 'P', '皿': 'M', '目': 'M', '矛': 'M', '矢': 'S', '石': 'S', '示': 'S', '禾': 'H', 
        '穴': 'X', '立': 'L', '竹': 'Z', '米': 'M', '糸': 'S', '缶': 'F', '网': 'W', '羊': 'Y', '羽': 'Y', '老': 'L', 
        '而': 'E', '耒': 'L', '耳': 'E', '肉': 'R', '臣': 'C', '自': 'Z', '至': 'Z', '臼': 'J', '舌': 'S', '舟': 'Z', 
        '艮': 'G', '色': 'S', '虫': 'C', '血': 'X', '行': 'X', '衣': 'Y', '西': 'X', '角': 'J', '言': 'Y', '谷': 'G', 
        '豆': 'D', '豕': 'S', '贝': 'B', '赤': 'C', '走': 'Z', '足': 'Z', '身': 'S', '车': 'C', '辛': 'X', '辰': 'C', 
        '里': 'L', '金': 'J', '长': 'C', '门': 'M', '隶': 'L', '雨': 'Y', '青': 'Q', '非': 'F', '面': 'M', '革': 'G', 
        '韦': 'W', '韭': 'J', '音': 'Y', '页': 'Y', '风': 'F', '飞': 'F', '食': 'S', '首': 'S', '香': 'X', '马': 'M', 
        '骨': 'G', '高': 'G', '鬼': 'G', '鱼': 'Y', '鸟': 'N', '卤': 'L', '鹿': 'L', '麦': 'M', '麻': 'M', '黄': 'H', 
        '黍': 'S', '鼎': 'D', '鼓': 'G', '鼠': 'S', '鼻': 'B', '齐': 'Q', '龙': 'L', '龟': 'G',
        
        # 常见中药名称的首字母
        '麻黄': 'MH', '桂枝': 'GZ', '甘草': 'GC', '杏仁': 'XR', '石膏': 'SG', '知母': 'ZM', '黄芩': 'HQ', '黄连': 'HL', 
        '黄柏': 'HB', '栀子': 'ZZ', '巴戟天': 'BJT', '当归': 'DG', '黄芪': 'HQ', '人参': 'RS', '白术': 'BS', '茯苓': 'FL', 
        '熟地': 'SD', '白芍': 'BS', '川芎': 'CX', '赤芍': 'SC', '白花蛇舌草': 'BHSSC', '荆芥': 'JJ', '防风': 'FF', '羌活': 'QH', 
        '独活': 'DH', '柴胡': 'CH', '前胡': 'QH', '桔梗': 'JG', '枳壳': 'ZK', '枳实': 'ZS', '木香': 'MX', '香附': 'XF', 
        '乌药': 'WY', '青皮': 'QP', '陈皮': 'CP', '佛手': 'FS', '香橼': 'XY', '薤白': 'XB', '大腹皮': 'DFP', '刀豆': 'DD', 
        '柿蒂': 'SD', '甘松': 'GS', '九香虫': 'JXC', '玫瑰花': 'MGG', '绿萼梅': 'LEM', '娑罗子': 'SLZ', '天仙藤': 'TX藤', 
        '路路通': 'LLT', '半边莲': 'BBL', '白花蛇': 'BHS', '蛇蜕': 'ST', '蜂房': 'FF', '土鳖虫': 'TBC', '水蛭': 'SZ', 
        '虻虫': 'MC', '斑蝥': 'BM', '穿山甲': 'CSJ', '王不留行': 'WBLX', '丝瓜络': 'SGL', '橘核': 'JH', '橘络': 'JL', 
        '橘叶': 'JY', '枸橘': 'GJ', '山楂': 'SZ', '神曲': 'SQ', '麦芽': 'MY', '谷芽': 'GY', '莱菔子': 'LFZ', '鸡内金': 'JNJ', 
        '鸡矢藤': 'JST', '隔山消': 'GSX', '阿魏': 'AW', '半夏': 'BX', '天南星': 'TNX', '禹白附': 'YBF', '白芥子': 'BJZ', 
        '皂荚': 'ZJ', '旋覆花': 'XFH', '白前': 'BQ', '前胡': 'QH', '桔梗': 'JG', '川贝母': 'CBM', '浙贝母': 'ZBM', 
        '瓜蒌': 'GL', '竹茹': 'ZR', '天竺黄': 'TZ黄', '前胡': 'QH', '桔梗': 'JG', '胖大海': 'PDH', '海藻': 'HZ', '昆布': 'KB', 
        '海蛤壳': 'HGK', '浮海石': 'FHS', '瓦楞子': 'WLZ', '礞石': 'MS', '龙骨': 'LG', '牡蛎': 'ML', '磁石': 'CS', '代赭石': 'DZS', 
        '刺蒺藜': 'CJL', '罗布麻': 'LBM', '生铁落': 'STL', '酸枣仁': 'SZR', '柏子仁': 'BZR', '远志': 'YZ', '合欢皮': 'HHP', 
        '合欢花': 'HH花', '夜交藤': 'YJT', '朱砂': 'ZS', '琥珀': 'HP', '珍珠': 'ZZ', '灵芝': 'LZ', '缬草': 'XC', '首乌藤': 'SWT', 
        '合欢花': 'HH花', '茯神': 'FS', '茯苓': 'FL', '猪苓': 'ZL', '泽泻': 'ZX', '薏苡仁': 'YIYR', '赤小豆': 'CXD', '冬瓜皮': 'DGP', 
        '冬瓜子': 'DGZ', '玉米须': 'YMX', '葫芦': 'HL', '香加皮': 'XJP', '五加皮': 'WJP', '桑寄生': 'SJS', '狗脊': 'GJ', 
        '千年健': 'QNJ', '雪莲花': 'XLH', '鹿衔草': 'LXC', '石楠叶': 'SNY', '海风藤': 'HFT', '青风藤': 'QFT', '丁公藤': 'DGT', 
        '昆明山海棠': 'KMSHT', '雷公藤': 'LGT', '川乌': 'CW', '草乌': 'CW', '附子': 'FZ', '肉桂': 'RG', '干姜': 'GJ', 
        '高良姜': 'GLJ', '吴茱萸': 'WZY', '小茴香': 'XHX', '丁香': 'DX', '花椒': 'HJ', '胡椒': 'HJ', '荜茇': 'BB', 
        '荜澄茄': 'BCQ', '山柰': 'SN', '大蒜': 'DS', '木香': 'MX', '沉香': 'CX', '檀香': 'TX', '川楝子': 'CLZ', '乌药': 'WY', 
        '青木香': 'QMX', '荔枝核': 'LZH', '香附': 'XF', '佛手': 'FS', '香橼': 'XY', '玫瑰花': 'MGG', '绿萼梅': 'LEM', 
        '娑罗子': 'SLZ', '薤白': 'XB', '天仙藤': 'TX藤', '大腹皮': 'DFP', '刀豆': 'DD', '柿蒂': 'SD', '甘松': 'GS', 
        '九香虫': 'JXC', '藿香': 'HX', '佩兰': 'PL', '苍术': 'CS', '厚朴': 'HP', '砂仁': 'SR', '白豆蔻': 'BDK', '草豆蔻': 'CDK', 
        '草果': 'CG', '茯苓': 'FL', '薏苡仁': 'YIYR', '猪苓': 'ZL', '泽泻': 'ZX', '冬瓜皮': 'DGP', '玉米须': 'YMX', '葫芦': 'HL', 
        '香加皮': 'XJP', '五加皮': 'WJP', '桑寄生': 'SJS', '狗脊': 'GJ', '千年健': 'QNJ', '雪莲花': 'XL花', '鹿衔草': 'LXC', 
        '石楠叶': 'SNY', '独活': 'DH', '威灵仙': 'WLX', '川乌': 'CW', '草乌': 'CW', '附子': 'FZ', '雷公藤': 'LGT', '伸筋草': 'SJC', 
        '寻骨风': 'XGF', '松节': 'SJ', '海风藤': 'HFT', '青风藤': 'QFT', '丁公藤': 'DGT', '昆明山海棠': 'KMSHT', '雪上一枝蒿': 'XSYZ', 
        '路路通': 'LLT', '穿破石': 'CPS', '丝瓜络': 'SGL', '防己': 'FJ', '秦艽': 'QJ', '络石藤': 'LST', '雷公藤': 'LGT', '老鹳草': 'LGC', 
        '穿山龙': 'CSL', '丝瓜络': 'SGL', '桑枝': 'SZ', '豨莶草': 'XLC', '臭梧桐': 'CWT', '海桐皮': 'HTP', '络石藤': 'LST', 
        '秦艽': 'QJ', '防己': 'FJ', '桑枝': 'SZ', '豨莶草': 'XLC', '臭梧桐': 'CWT', '海桐皮': 'HTP', '络石藤': 'LST', '秦艽': 'QJ', 
        '防己': 'FJ', '桑枝': 'SZ', '豨莶草': 'XLC', '臭梧桐': 'CWT', '海桐皮': 'HTP', '络石藤': 'LST', '秦艽': 'QJ', '防己': 'FJ', '桑枝': 'SZ', 
        '豨莶草': 'XLC', '臭梧桐': 'CWT', '海桐皮': 'HTP', '络石藤': 'LST', '秦艽': 'QJ', '防己': 'FJ', '桑枝': 'SZ', '豨莶草': 'XLC', '臭梧桐': 'CWT', 
        '海桐皮': 'HTP', '络石藤': 'LST', '秦艽': 'QJ', '防己': 'FJ', '桑枝': 'SZ', '豨莶草': 'XLC', '臭梧桐': 'CWT', '海桐皮': 'HTP', 
        '络石藤': 'LST', '秦艽': 'QJ', '防己': 'FJ', '桑枝': 'SZ', '豨莶草': 'XLC', '臭梧桐': 'CWT', '海桐皮': 'HTP', '络石藤': 'LST', '秦艽': 'QJ', '防己': 'FJ', '桑枝': 'SZ', '豨莶草': 'XLC', '臭梧桐': 'CWT', '海桐皮': 'HTP', 
        '络石藤': 'LST'
    }
    
    # 生成首字母缩写
    initials = []
    i = 0
    name_length = len(name)
    
    while i < name_length:
        # 尝试匹配多字药材名称
        matched = False
        # 从最长可能的长度开始尝试
        for length in range(min(5, name_length - i), 0, -1):
            substring = name[i:i+length]
            if substring in pinyin_map:
                initials.append(pinyin_map[substring])
                i += length
                matched = True
                break
        
        # 如果没有匹配到多字名称，尝试匹配单字
        if not matched:
            char = name[i]
            if char in pinyin_map:
                initials.append(pinyin_map[char])
            else:
                # 对于不在映射表中的字符，使用原字符
                initials.append(char)
            i += 1
    
    result = ''.join(initials).upper()
    
    # 特殊处理：如果结果与原名称相同（说明没有匹配到任何首字母），则使用拼音首字母
    if result == name.upper():
        # 简单的拼音首字母映射，覆盖常见中药材字符
        simple_map = {
            '白': 'B', '花': 'H', '蛇': 'S', '舌': 'S', '草': 'C', '荆': 'J', '芥': 'J', '防': 'F', '风': 'F',
            '羌': 'Q', '活': 'H', '独': 'D', '柴': 'C', '胡': 'H', '前': 'Q', '桔': 'J', '梗': 'G', '枳': 'Z',
            '壳': 'K', '实': 'S', '木': 'M', '香': 'X', '附': 'F', '乌': 'W', '药': 'Y', '青': 'Q', '陈': 'C',
            '佛': 'F', '手': 'S', '橼': 'Y', '薤': 'X', '白': 'B', '大': 'D', '腹': 'F', '皮': 'P', '刀': 'D',
            '豆': 'D', '柿': 'S', '蒂': 'D', '甘': 'G', '松': 'S', '九': 'J', '虫': 'C', '玫': 'M', '瑰': 'G',
            '花': 'H', '绿': 'L', '萼': 'E', '梅': 'M', '娑': 'S', '罗': 'L', '子': 'Z', '天': 'T', '仙': 'X',
            '藤': 'T', '路': 'L', '通': 'T', '半': 'B', '边': 'B', '莲': 'L', '蜕': 'T', '蜂': 'F', '房': 'F',
            '土': 'T', '鳖': 'B', '水': 'S', '蛭': 'Z', '虻': 'M', '斑': 'B', '蝥': 'M', '穿': 'C', '山': 'S',
            '甲': 'J', '王': 'W', '不': 'B', '留': 'L', '行': 'X', '丝': 'S', '瓜': 'G', '络': 'L', '橘': 'J',
            '核': 'H', '叶': 'Y', '枸': 'G', '山': 'S', '楂': 'Z', '神': 'S', '曲': 'Q', '麦': 'M', '芽': 'Y',
            '谷': 'G', '莱': 'L', '菔': 'F', '子': 'Z', '鸡': 'J', '内': 'N', '金': 'J', '矢': 'S', '藤': 'T',
            '隔': 'G', '消': 'X', '阿': 'A', '魏': 'W', '半': 'B', '夏': 'X', '天': 'T', '南': 'N', '星': 'X',
            '禹': 'Y', '附': 'F', '芥': 'J', '子': 'Z', '皂': 'Z', '荚': 'J', '旋': 'X', '覆': 'F', '花': 'H',
            '前': 'Q', '胡': 'H', '桔': 'J', '梗': 'G', '川': 'C', '贝': 'B', '母': 'M', '浙': 'Z', '瓜': 'G',
            '蒌': 'L', '竹': 'Z', '茹': 'R', '天': 'T', '竺': 'Z', '黄': 'H', '胖': 'P', '大': 'D', '海': 'H',
            '海': 'H', '藻': 'Z', '昆': 'K', '布': 'B', '蛤': 'G', '壳': 'K', '浮': 'F', '石': 'S', '瓦': 'W',
            '楞': 'L', '子': 'Z', '礞': 'M', '龙': 'L', '骨': 'G', '牡': 'M', '蛎': 'L', '磁': 'C', '代': 'D',
            '赭': 'Z', '刺': 'C', '蒺': 'J', '藜': 'L', '罗': 'L', '布': 'B', '麻': 'M', '生': 'S', '铁': 'T',
            '落': 'L', '酸': 'S', '枣': 'Z', '仁': 'R', '柏': 'B', '远': 'Y', '志': 'Z', '合': 'H', '欢': 'H',
            '夜': 'Y', '交': 'J', '朱': 'Z', '砂': 'S', '琥': 'H', '珀': 'P', '珍': 'Z', '珠': 'Z', '灵': 'L',
            '芝': 'Z', '缬': 'X', '草': 'C', '首': 'S', '乌': 'W', '茯': 'F', '神': 'S', '猪': 'Z', '苓': 'L',
            '泽': 'Z', '泻': 'X', '薏': 'Y', '苡': 'Y', '仁': 'R', '赤': 'C', '小': 'X', '豆': 'D', '冬': 'D',
            '瓜': 'G', '玉': 'Y', '米': 'M', '须': 'X', '葫': 'H', '芦': 'L', '加': 'J', '五': 'W', '桑': 'S',
            '寄': 'J', '生': 'S', '狗': 'G', '脊': 'J', '千': 'Q', '年': 'N', '健': 'J', '雪': 'X', '莲': 'L',
            '鹿': 'L', '衔': 'X', '石': 'S', '楠': 'N', '叶': 'Y', '海': 'H', '风': 'F', '青': 'Q', '丁': 'D',
            '公': 'G', '昆': 'K', '明': 'M', '雷': 'L', '川': 'C', '草': 'C', '附': 'F', '肉': 'R', '桂': 'G',
            '干': 'G', '姜': 'J', '高': 'G', '良': 'L', '吴': 'W', '茱': 'Z', '萸': 'Y', '小': 'X', '茴': 'H',
            '香': 'X', '丁': 'D', '花': 'H', '椒': 'J', '胡': 'H', '荜': 'B', '茇': 'B', '澄': 'C', '茄': 'Q',
            '山': 'S', '柰': 'N', '大': 'D', '蒜': 'S', '沉': 'C', '檀': 'T', '川': 'C', '楝': 'L', '荔': 'L',
            '枝': 'Z', '核': 'H', '佛': 'F', '手': 'S', '香': 'X', '橼': 'Y', '玫': 'M', '瑰': 'G', '绿': 'L',
            '萼': 'E', '梅': 'M', '娑': 'S', '罗': 'L', '子': 'Z', '薤': 'X', '白': 'B', '天': 'T', '仙': 'X',
            '藤': 'T', '大': 'D', '腹': 'F', '皮': 'P', '刀': 'D', '豆': 'D', '柿': 'S', '蒂': 'D', '甘': 'G',
            '松': 'S', '九': 'J', '香': 'X', '虫': 'C', '藿': 'H', '香': 'X', '佩': 'P', '兰': 'L', '苍': 'C',
            '术': 'S', '厚': 'H', '朴': 'P', '砂': 'S', '仁': 'R', '白': 'B', '豆': 'D', '蔻': 'K', '草': 'C',
            '果': 'G', '猪': 'Z', '苓': 'L', '泽': 'Z', '泻': 'X', '冬': 'D', '瓜': 'G', '皮': 'P', '玉': 'Y',
            '米': 'M', '须': 'X', '葫': 'H', '芦': 'L', '加': 'J', '五': 'W', '桑': 'S', '寄': 'J', '生': 'S',
            '狗': 'G', '脊': 'J', '千': 'Q', '年': 'N', '健': 'J', '雪': 'X', '莲': 'L', '鹿': 'L', '衔': 'X',
            '石': 'S', '楠': 'N', '叶': 'Y', '独': 'D', '活': 'H', '威': 'W', '灵': 'L', '仙': 'X', '川': 'C',
            '草': 'C', '附': 'F', '雷': 'L', '公': 'G', '藤': 'T', '伸': 'S', '筋': 'J', '草': 'C', '寻': 'X',
            '骨': 'G', '风': 'F', '松': 'S', '节': 'J', '海': 'H', '风': 'F', '青': 'Q', '丁': 'D', '公': 'G',
            '昆': 'K', '明': 'M', '雪': 'X', '上': 'S', '一': 'Y', '枝': 'Z', '蒿': 'H', '路': 'L', '路': 'L',
            '通': 'T', '穿': 'C', '破': 'P', '石': 'S', '丝': 'S', '瓜': 'G', '络': 'L', '防': 'F', '己': 'J',
            '秦': 'Q', '艽': 'J', '络': 'L', '石': 'S', '老': 'L', '鹳': 'G', '草': 'C', '穿': 'C', '山': 'S',
            '龙': 'L', '桑': 'S', '枝': 'Z', '豨': 'X', '莶': 'X', '草': 'C', '臭': 'C', '梧': 'W', '桐': 'T',
            '海': 'H', '桐': 'T', '皮': 'P'
        }
        
        # 重新生成首字母缩写
        fallback_initials = []
        for char in name:
            if char in simple_map:
                fallback_initials.append(simple_map[char])
            else:
                fallback_initials.append(char)
        result = ''.join(fallback_initials).upper()
    
    return result

# 可点击的标签类
class ClickableLabel(ButtonBehavior, Label):
    ''' 可点击的标签，提供触摸反馈 '''
    def __init__(self, **kwargs):
        super(ClickableLabel, self).__init__(**kwargs)
        self.background_color = (0.9, 0.9, 0.9, 1)
        self.border = (16, 16, 16, 16)

    def on_press(self):
        ''' 按下时的效果 '''
        self.background_color = (0.7, 0.7, 0.7, 1)

    def on_release(self):
        ''' 释放时的效果 '''
        self.background_color = (0.9, 0.9, 0.9, 1)

# 可选择的RecycleView
class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    ''' Adds selection and focus behavior to the view. '''

class SelectableLabel(RecycleDataViewBehavior, ClickableLabel):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        if is_selected:
            print("selection changed to {0}".format(rv.data[index]))
            self.background_color = (0.6, 0.8, 1, 1)
        else:
            self.background_color = (0.9, 0.9, 0.9, 1)

# 主应用类
class ChineseMedicinePrescriptionSystem(App):
    def build(self):
        self.db = DatabaseManager()
        return MainWindow(db=self.db)

# 主窗口类
class MainWindow(BoxLayout):
    def __init__(self, db, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.db = db
        self.orientation = 'vertical'
        # 监听窗口大小变化
        from kivy.core.window import Window
        Window.bind(size=self.on_window_size)
        self.create_main_ui()
    
    def on_window_size(self, instance, size):
        # 当窗口大小变化时，更新所有标签页的布局
        for tab in self.tabbed_panel.tab_list:
            if hasattr(tab.content, 'update_layout'):
                tab.content.update_layout(size)
    
    def create_main_ui(self):
        # 创建标签页
        self.tabbed_panel = TabbedPanel()
        self.tabbed_panel.do_default_tab = False
        
        # 患者信息标签页
        patient_tab = TabbedPanelItem(text='患者信息')
        patient_tab.content = PatientTab(db=self.db)
        self.tabbed_panel.add_widget(patient_tab)
        
        # 处方开具标签页
        prescription_tab = TabbedPanelItem(text='处方开具')
        prescription_tab.content = PrescriptionTab(db=self.db)
        self.tabbed_panel.add_widget(prescription_tab)
        
        # 药品管理标签页
        medicine_tab = TabbedPanelItem(text='药品管理')
        medicine_tab.content = MedicineTab(db=self.db)
        self.tabbed_panel.add_widget(medicine_tab)
        
        # 处方历史标签页
        history_tab = TabbedPanelItem(text='处方历史')
        history_tab.content = HistoryTab(db=self.db)
        self.tabbed_panel.add_widget(history_tab)
        
        # 方剂模板标签页
        formula_tab = TabbedPanelItem(text='方剂模板')
        formula_tab.content = FormulaTab(db=self.db)
        self.tabbed_panel.add_widget(formula_tab)
        
        # 设置标签页
        settings_tab = TabbedPanelItem(text='设置')
        settings_tab.content = SettingsTab(db=self.db)
        self.tabbed_panel.add_widget(settings_tab)
        
        self.add_widget(self.tabbed_panel)

# 患者信息标签页
class PatientTab(BoxLayout):
    def __init__(self, db, **kwargs):
        super(PatientTab, self).__init__(**kwargs)
        self.db = db
        self.orientation = 'vertical'
        self.create_ui()
    
    def create_ui(self):
        # 患者信息输入
        self.input_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.input_frame.add_widget(Label(text='患者信息输入', font_size=16, bold=True))
        
        # 表单布局
        self.form_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=dp(200))
        
        self.form_layout.add_widget(Label(text='姓名:'))
        self.name_input = TextInput(multiline=False)
        self.form_layout.add_widget(self.name_input)
        
        self.form_layout.add_widget(Label(text='性别:'))
        self.gender_spinner = Spinner(text='男', values=['男', '女'])
        self.form_layout.add_widget(self.gender_spinner)
        
        self.form_layout.add_widget(Label(text='年龄:'))
        self.age_input = TextInput(multiline=False, input_filter='int')
        self.form_layout.add_widget(self.age_input)
        
        self.form_layout.add_widget(Label(text='地址:'))
        self.address_input = TextInput(multiline=False)
        self.form_layout.add_widget(self.address_input)
        
        self.form_layout.add_widget(Label(text='电话:'))
        self.phone_input = TextInput(multiline=False)
        self.form_layout.add_widget(self.phone_input)
        
        self.input_frame.add_widget(self.form_layout)
        
        # 按钮布局
        self.button_layout = BoxLayout(size_hint_y=None, height=dp(60), spacing=10)
        self.button_layout.add_widget(Button(text='添加患者', on_press=self.add_patient, size_hint_y=None, height=dp(50)))
        self.button_layout.add_widget(Button(text='清空', on_press=self.clear_fields, size_hint_y=None, height=dp(50)))
        self.button_layout.add_widget(Button(text='全选', on_press=self.select_all, size_hint_y=None, height=dp(50)))
        self.button_layout.add_widget(Button(text='批量删除', on_press=self.batch_delete, size_hint_y=None, height=dp(50)))
        self.button_layout.add_widget(Button(text='历史就诊', on_press=self.view_history, size_hint_y=None, height=dp(50)))
        
        self.input_frame.add_widget(self.button_layout)
        self.add_widget(self.input_frame)
        
        # 患者列表
        self.list_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.list_frame.add_widget(Label(text='患者列表', font_size=16, bold=True))
        
        # 搜索框
        self.search_layout = BoxLayout(size_hint_y=None, height=dp(40))
        self.search_layout.add_widget(Label(text='搜索:'))
        self.search_input = TextInput(multiline=False)
        self.search_input.bind(text=self.search_patients)
        self.search_layout.add_widget(self.search_input)
        self.list_frame.add_widget(self.search_layout)
        
        # 患者列表
        self.patient_list = RecycleView()
        self.patient_list.data = []
        self.patient_list.viewclass = 'SelectableLabel'
        layout_manager = SelectableRecycleBoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        layout_manager.bind(minimum_height=layout_manager.setter('height'))
        self.patient_list.add_widget(layout_manager)
        self.list_frame.add_widget(self.patient_list)
        
        self.add_widget(self.list_frame)
        self.load_patients()
    
    def update_layout(self, size):
        # 根据屏幕尺寸调整布局
        width, height = size
        
        # 调整表单布局列数
        if width < 600:  # 手机屏幕
            self.form_layout.cols = 1
            self.form_layout.height = dp(300)
            # 调整按钮布局为垂直
            self.button_layout.orientation = 'vertical'
            self.button_layout.height = dp(150)
        else:  # 平板或更大屏幕
            self.form_layout.cols = 2
            self.form_layout.height = dp(200)
            # 调整按钮布局为水平
            self.button_layout.orientation = 'horizontal'
            self.button_layout.height = dp(60)
    
    def add_patient(self, instance):
        name = self.name_input.text
        gender = self.gender_spinner.text
        age = self.age_input.text
        address = self.address_input.text
        phone = self.phone_input.text
        
        if not name or not gender or not age:
            self.show_popup('错误', '姓名、性别和年龄不能为空')
            return
        
        try:
            age = int(age)
        except ValueError:
            self.show_popup('错误', '年龄必须是数字')
            return
        
        # 插入患者数据
        try:
            self.db.cursor.execute('''
            INSERT INTO patients (name, gender, age, address, phone) VALUES (?, ?, ?, ?, ?)
            ''', (name, gender, age, address, phone))
            self.db.conn.commit()
            
            self.show_popup('成功', '患者添加成功')
            self.clear_fields()
            self.load_patients()
        except Exception as e:
            self.show_popup('错误', f'添加患者失败: {str(e)}')
    
    def clear_fields(self, instance=None):
        self.name_input.text = ''
        self.gender_spinner.text = '男'
        self.age_input.text = ''
        self.address_input.text = ''
        self.phone_input.text = ''
    
    def load_patients(self, search_term=''):
        # 清空列表
        self.patient_list.data = []
        
        # 加载患者数据
        if search_term:
            self.db.cursor.execute("SELECT * FROM patients WHERE name LIKE ? OR address LIKE ? OR phone LIKE ?", 
                              (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        else:
            self.db.cursor.execute("SELECT * FROM patients")
        patients = self.db.cursor.fetchall()
        
        for patient in patients:
            patient_info = f"姓名: {patient[1]}, 性别: {patient[2]}, 年龄: {patient[3]}, 地址: {patient[4]}, 电话: {patient[5]}"
            self.patient_list.data.append({'text': patient_info, 'size_hint_y': None, 'height': dp(40)})
    
    def search_patients(self, instance, value):
        self.load_patients(value)
    
    def select_all(self, instance):
        # 实现全选功能
        pass
    
    def batch_delete(self, instance):
        # 实现批量删除功能
        pass
    
    def view_history(self, instance):
        # 实现历史就诊功能
        pass
    
    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

# 处方开具标签页
class PrescriptionTab(BoxLayout):
    def __init__(self, db, **kwargs):
        super(PrescriptionTab, self).__init__(**kwargs)
        self.db = db
        self.orientation = 'vertical'
        self.create_ui()
    
    def create_ui(self):
        # 主内容区域
        self.main_content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 患者信息
        self.patient_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.patient_frame.add_widget(Label(text='患者信息', font_size=16, bold=True))
        
        # 患者下拉列表
        patient_row = BoxLayout(size_hint_y=None, height=dp(40))
        patient_row.add_widget(Label(text='患者:', size_hint_x=0.2))
        self.patient_spinner = Spinner(text='选择患者', values=[])
        self.patient_spinner.size_hint_x=0.8
        patient_row.add_widget(self.patient_spinner)
        self.patient_frame.add_widget(patient_row)
        
        # 诊断输入
        diagnosis_row = BoxLayout(size_hint_y=None, height=dp(40))
        diagnosis_row.add_widget(Label(text='诊断:', size_hint_x=0.2))
        self.diagnosis_input = TextInput(multiline=False)
        self.diagnosis_input.size_hint_x=0.8
        diagnosis_row.add_widget(self.diagnosis_input)
        self.patient_frame.add_widget(diagnosis_row)
        
        # 性别
        gender_row = BoxLayout(size_hint_y=None, height=dp(40))
        gender_row.add_widget(Label(text='性别:', size_hint_x=0.2))
        self.gender_spinner = Spinner(text='男', values=['男', '女'])
        self.gender_spinner.size_hint_x=0.8
        gender_row.add_widget(self.gender_spinner)
        self.patient_frame.add_widget(gender_row)
        
        # 年龄
        age_row = BoxLayout(size_hint_y=None, height=dp(40))
        age_row.add_widget(Label(text='年龄:', size_hint_x=0.2))
        self.age_input = TextInput(multiline=False, input_filter='int')
        self.age_input.size_hint_x=0.8
        age_row.add_widget(self.age_input)
        self.patient_frame.add_widget(age_row)
        
        # 地址
        address_row = BoxLayout(size_hint_y=None, height=dp(40))
        address_row.add_widget(Label(text='地址:', size_hint_x=0.2))
        self.address_input = TextInput(multiline=False)
        self.address_input.size_hint_x=0.8
        address_row.add_widget(self.address_input)
        self.patient_frame.add_widget(address_row)
        
        # 电话
        phone_row = BoxLayout(size_hint_y=None, height=dp(40))
        phone_row.add_widget(Label(text='电话:', size_hint_x=0.2))
        self.phone_input = TextInput(multiline=False)
        self.phone_input.size_hint_x=0.8
        phone_row.add_widget(self.phone_input)
        self.patient_frame.add_widget(phone_row)
        
        self.main_content.add_widget(self.patient_frame)
        
        # 病历信息
        self.medical_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.medical_frame.add_widget(Label(text='病历信息', font_size=16, bold=True))
        
        # 主诉
        chief_complaint_row = BoxLayout(size_hint_y=None, height=dp(40))
        chief_complaint_row.add_widget(Label(text='主诉:', size_hint_x=0.2))
        self.chief_complaint_input = TextInput(multiline=False)
        self.chief_complaint_input.size_hint_x=0.8
        chief_complaint_row.add_widget(self.chief_complaint_input)
        self.medical_frame.add_widget(chief_complaint_row)
        
        # 现病史
        present_illness_row = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80))
        present_illness_row.add_widget(Label(text='现病史:'))
        self.present_illness_input = TextInput(multiline=True)
        present_illness_row.add_widget(self.present_illness_input)
        self.medical_frame.add_widget(present_illness_row)
        
        # 既往史
        past_history_row = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80))
        past_history_row.add_widget(Label(text='既往史:'))
        self.past_history_input = TextInput(multiline=True)
        past_history_row.add_widget(self.past_history_input)
        self.medical_frame.add_widget(past_history_row)
        
        # 过敏史
        allergy_history_row = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(60))
        allergy_history_row.add_widget(Label(text='过敏史:'))
        self.allergy_history_input = TextInput(multiline=True)
        allergy_history_row.add_widget(self.allergy_history_input)
        self.medical_frame.add_widget(allergy_history_row)
        
        # 保存按钮
        save_frame = BoxLayout(size_hint_y=None, height=dp(40))
        save_frame.add_widget(Button(text='保存修改', on_press=self.save_medical_info))
        self.medical_frame.add_widget(save_frame)
        
        self.main_content.add_widget(self.medical_frame)
        
        # 药品选择和处方区域
        self.medicine_prescription_frame = BoxLayout(orientation='horizontal', spacing=10)
        
        # 方剂模板选择
        self.formula_frame = BoxLayout(orientation='vertical', size_hint_x=0.3, padding=10, spacing=10)
        self.formula_frame.add_widget(Label(text='方剂模板选择', font_size=14, bold=True))
        
        # 方剂搜索
        formula_search = BoxLayout(size_hint_y=None, height=dp(40))
        formula_search.add_widget(Label(text='搜索:'))
        self.formula_search_input = TextInput(multiline=False)
        self.formula_search_input.bind(text=self.search_formulas)
        formula_search.add_widget(self.formula_search_input)
        self.formula_frame.add_widget(formula_search)
        
        # 方剂列表
        self.formula_list = RecycleView()
        self.formula_list.data = []
        self.formula_list.viewclass = 'SelectableLabel'
        layout_manager = SelectableRecycleBoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        layout_manager.bind(minimum_height=layout_manager.setter('height'))
        self.formula_list.add_widget(layout_manager)
        self.formula_frame.add_widget(self.formula_list)
        
        # 添加方剂按钮
        self.formula_frame.add_widget(Button(text='添加方剂到处方', on_press=self.add_formula_to_prescription))
        
        self.medicine_prescription_frame.add_widget(self.formula_frame)
        
        # 药品选择
        self.medicine_frame = BoxLayout(orientation='vertical', size_hint_x=0.3, padding=10, spacing=10)
        self.medicine_frame.add_widget(Label(text='药品选择', font_size=14, bold=True))
        
        # 药品搜索
        medicine_search = BoxLayout(size_hint_y=None, height=dp(40))
        medicine_search.add_widget(Label(text='搜索:'))
        self.medicine_search_input = TextInput(multiline=False)
        self.medicine_search_input.bind(text=self.search_medicines)
        medicine_search.add_widget(self.medicine_search_input)
        self.medicine_frame.add_widget(medicine_search)
        
        # 药品列表
        self.medicine_list = RecycleView()
        self.medicine_list.data = []
        self.medicine_list.viewclass = 'SelectableLabel'
        layout_manager = SelectableRecycleBoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        layout_manager.bind(minimum_height=layout_manager.setter('height'))
        self.medicine_list.add_widget(layout_manager)
        self.medicine_frame.add_widget(self.medicine_list)
        
        # 数量输入
        quantity_frame = BoxLayout(size_hint_y=None, height=dp(40))
        quantity_frame.add_widget(Label(text='数量:'))
        self.quantity_input = TextInput(multiline=False, text='10')
        quantity_frame.add_widget(self.quantity_input)
        self.medicine_frame.add_widget(quantity_frame)
        
        # 药品操作按钮
        self.medicine_buttons = BoxLayout(size_hint_y=None, height=dp(80), orientation='vertical', spacing=5)
        self.medicine_buttons.add_widget(Button(text='添加到处方', on_press=self.add_medicine_to_prescription))
        self.medicine_buttons.add_widget(Button(text='从处方移除', on_press=self.remove_medicine_from_prescription))
        self.medicine_buttons.add_widget(Button(text='清空处方', on_press=self.clear_prescription))
        self.medicine_frame.add_widget(self.medicine_buttons)
        
        self.medicine_prescription_frame.add_widget(self.medicine_frame)
        
        # 处方药品
        self.prescription_frame = BoxLayout(orientation='vertical', size_hint_x=0.4, padding=10, spacing=10)
        self.prescription_frame.add_widget(Label(text='处方药品', font_size=14, bold=True))
        
        # 处方药品列表
        self.prescription_list = RecycleView()
        self.prescription_list.data = []
        self.prescription_list.viewclass = 'SelectableLabel'
        layout_manager = SelectableRecycleBoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        layout_manager.bind(minimum_height=layout_manager.setter('height'))
        self.prescription_list.add_widget(layout_manager)
        self.prescription_frame.add_widget(self.prescription_list)
        
        # 药剂信息
        self.medicine_info_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.medicine_info_frame.add_widget(Label(text='药剂信息', font_size=14, bold=True))
        
        # 代煎、外配、院内制剂选项
        self.option_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.decoct_checkbox = CheckBox()
        self.option_frame.add_widget(self.decoct_checkbox)
        self.option_frame.add_widget(Label(text='代煎'))
        
        self.external_checkbox = CheckBox()
        self.option_frame.add_widget(self.external_checkbox)
        self.option_frame.add_widget(Label(text='外配'))
        
        self.hospital_checkbox = CheckBox()
        self.option_frame.add_widget(self.hospital_checkbox)
        self.option_frame.add_widget(Label(text='院内制剂'))
        self.medicine_info_frame.add_widget(self.option_frame)
        
        # 医保/自费选项
        payment_frame = BoxLayout(size_hint_y=None, height=dp(40))
        payment_frame.add_widget(Label(text='医保/自费:'))
        self.payment_spinner = Spinner(text='自费', values=['医保', '自费'])
        payment_frame.add_widget(self.payment_spinner)
        self.medicine_info_frame.add_widget(payment_frame)
        
        # 药剂数、剂型、频次等
        self.detail_frame1 = BoxLayout(size_hint_y=None, height=dp(40))
        self.detail_frame1.add_widget(Label(text='草药剂数:'))
        self.medicine_count_input = TextInput(multiline=False, text='7')
        self.detail_frame1.add_widget(self.medicine_count_input)
        
        self.detail_frame1.add_widget(Label(text='采用剂型:'))
        self.dosage_form_spinner = Spinner(text='汤剂', values=['免煎', '汤剂', '丸剂', '散剂'])
        self.detail_frame1.add_widget(self.dosage_form_spinner)
        
        self.detail_frame1.add_widget(Label(text='频次:'))
        self.frequency_spinner = Spinner(text='一日两次', values=['一次', '一日一次', '一日两次', '一日三次'])
        self.detail_frame1.add_widget(self.frequency_spinner)
        self.medicine_info_frame.add_widget(self.detail_frame1)
        
        # 用药方法和服用要求
        detail_frame2 = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80))
        detail_frame2.add_widget(Label(text='用药方法:'))
        self.usage_spinner = Spinner(text='水煎服,1日1剂,1日2次', values=['水煎服,1日1剂,1日2次', '水煎服,1日1剂,1日3次', '温水送服,1日2次'])
        detail_frame2.add_widget(self.usage_spinner)
        
        detail_frame2.add_widget(Label(text='服用要求:'))
        self.requirements_input = TextInput(multiline=False)
        detail_frame2.add_widget(self.requirements_input)
        self.medicine_info_frame.add_widget(detail_frame2)
        
        self.prescription_frame.add_widget(self.medicine_info_frame)
        
        self.medicine_prescription_frame.add_widget(self.prescription_frame)
        
        self.main_content.add_widget(self.medicine_prescription_frame)
        
        # 底部操作区域
        self.bottom_frame = BoxLayout(size_hint_y=None, height=dp(50), spacing=10)
        self.bottom_frame.add_widget(Label(text='总金额:'))
        self.total_price_label = Label(text='0.00')
        self.bottom_frame.add_widget(self.total_price_label)
        
        self.bottom_frame.add_widget(Button(text='AI处方', on_press=self.generate_ai_prescription))
        self.bottom_frame.add_widget(Button(text='打印处方', on_press=self.print_prescription))
        self.bottom_frame.add_widget(Button(text='保存处方', on_press=self.save_prescription))
        
        self.main_content.add_widget(self.bottom_frame)
        self.add_widget(self.main_content)
        
        # 加载患者和药品数据
        self.load_patients()
        self.load_medicines()
        self.load_formulas()
    
    def update_layout(self, size):
        # 根据屏幕尺寸调整布局
        width, height = size
        
        if width < 700:  # 手机屏幕
            # 调整药品选择和处方区域为垂直布局
            self.medicine_prescription_frame.orientation = 'vertical'
            
            # 调整各部分的大小
            self.formula_frame.size_hint_y = 0.3
            self.medicine_frame.size_hint_y = 0.3
            self.prescription_frame.size_hint_y = 0.4
            
            # 调整药剂信息布局
            self.option_frame.orientation = 'vertical'
            self.option_frame.height = dp(80)
            
            self.detail_frame1.orientation = 'vertical'
            self.detail_frame1.height = dp(120)
            
            # 调整底部按钮布局
            self.bottom_frame.orientation = 'vertical'
            self.bottom_frame.height = dp(150)
        else:  # 平板或更大屏幕
            # 调整药品选择和处方区域为水平布局
            self.medicine_prescription_frame.orientation = 'horizontal'
            
            # 调整各部分的大小
            self.formula_frame.size_hint_x = 0.3
            self.formula_frame.size_hint_y = None
            self.medicine_frame.size_hint_x = 0.3
            self.medicine_frame.size_hint_y = None
            self.prescription_frame.size_hint_x = 0.4
            self.prescription_frame.size_hint_y = None
            
            # 调整药剂信息布局
            self.option_frame.orientation = 'horizontal'
            self.option_frame.height = dp(40)
            
            self.detail_frame1.orientation = 'horizontal'
            self.detail_frame1.height = dp(40)
            
            # 调整底部按钮布局
            self.bottom_frame.orientation = 'horizontal'
            self.bottom_frame.height = dp(50)
    
    def load_patients(self):
        # 加载患者到下拉列表
        self.db.cursor.execute("SELECT id, name FROM patients")
        patients = self.db.cursor.fetchall()
        patient_list = [f"{p[0]}: {p[1]}" for p in patients]
        self.patient_spinner.values = patient_list
    
    def load_medicines(self, search_term=''):
        # 清空药品列表
        self.medicine_list.data = []
        
        # 加载药品数据
        if search_term:
            self.db.cursor.execute("SELECT id, name, unit, sale_price FROM medicines WHERE name LIKE ? OR pinyin LIKE ?", ("%" + search_term + "%", "%" + search_term.upper() + "%"))
        else:
            self.db.cursor.execute("SELECT id, name, unit, sale_price FROM medicines")
        medicines = self.db.cursor.fetchall()
        
        for medicine in medicines:
            medicine_info = f"{medicine[1]} ({medicine[2]}) - {medicine[3]}元"
            self.medicine_list.data.append({'text': medicine_info, 'size_hint_y': None, 'height': dp(30)})
    
    def load_formulas(self, search_term=''):
        # 清空方剂列表
        self.formula_list.data = []
        
        # 加载方剂模板数据
        if search_term:
            self.db.cursor.execute("SELECT name, description, ingredients FROM formulas WHERE name LIKE ? OR description LIKE ?", 
                              (f"%{search_term}%", f"%{search_term}%"))
        else:
            self.db.cursor.execute("SELECT name, description, ingredients FROM formulas")
        formulas = self.db.cursor.fetchall()
        
        for formula in formulas:
            formula_info = f"{formula[0]} - {formula[1]}"
            self.formula_list.data.append({'text': formula_info, 'size_hint_y': None, 'height': dp(30)})
    
    def search_medicines(self, instance, value):
        self.load_medicines(value)
    
    def search_formulas(self, instance, value):
        self.load_formulas(value)
    
    def add_medicine_to_prescription(self, instance):
        # 实现添加药品到处方的功能
        pass
    
    def remove_medicine_from_prescription(self, instance):
        # 实现从处方移除药品的功能
        pass
    
    def clear_prescription(self, instance):
        # 实现清空处方的功能
        pass
    
    def save_medical_info(self, instance):
        # 实现保存病历信息的功能
        pass
    
    def add_formula_to_prescription(self, instance):
        # 实现添加方剂到处方的功能
        pass
    
    def generate_ai_prescription(self, instance):
        # 实现AI处方生成功能
        pass
    
    def print_prescription(self, instance):
        # 实现打印处方的功能
        pass
    
    def save_prescription(self, instance):
        # 实现保存处方的功能
        pass

# 药品管理标签页
class MedicineTab(BoxLayout):
    def __init__(self, db, **kwargs):
        super(MedicineTab, self).__init__(**kwargs)
        self.db = db
        self.orientation = 'vertical'
        self.create_ui()
    
    def create_ui(self):
        # 药品信息输入
        self.input_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.input_frame.add_widget(Label(text='药品信息输入', font_size=16, bold=True))
        
        # 表单布局
        self.form_layout = GridLayout(cols=4, spacing=10, size_hint_y=None, height=dp(100))
        
        self.form_layout.add_widget(Label(text='药品名称:'))
        self.name_input = TextInput(multiline=False)
        self.form_layout.add_widget(self.name_input)
        
        self.form_layout.add_widget(Label(text='单位:'))
        self.unit_input = TextInput(multiline=False)
        self.form_layout.add_widget(self.unit_input)
        
        self.form_layout.add_widget(Label(text='进价:'))
        self.price_input = TextInput(multiline=False, input_filter='float')
        self.form_layout.add_widget(self.price_input)
        
        self.form_layout.add_widget(Label(text='售价:'))
        self.sale_price_input = TextInput(multiline=False, input_filter='float')
        self.form_layout.add_widget(self.sale_price_input)
        
        self.input_frame.add_widget(self.form_layout)
        
        # 批量修改售价
        self.batch_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.batch_frame.add_widget(Label(text='批量修改售价倍率:'))
        self.batch_rate_input = TextInput(multiline=False, text='1.5')
        self.batch_frame.add_widget(self.batch_rate_input)
        self.batch_frame.add_widget(Button(text='批量修改售价', on_press=self.batch_update_sale_price))
        self.input_frame.add_widget(self.batch_frame)
        
        # 按钮布局
        self.button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=10)
        self.button_layout.add_widget(Button(text='添加药品', on_press=self.add_medicine))
        self.button_layout.add_widget(Button(text='清空', on_press=self.clear_fields))
        self.button_layout.add_widget(Button(text='从Excel导入', on_press=self.import_from_excel))
        self.button_layout.add_widget(Button(text='下载导入模板', on_press=self.download_template))
        self.button_layout.add_widget(Button(text='全选', on_press=self.select_all))
        self.button_layout.add_widget(Button(text='批量删除', on_press=self.batch_delete))
        
        self.input_frame.add_widget(self.button_layout)
        self.add_widget(self.input_frame)
        
        # 药品列表
        self.list_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.list_frame.add_widget(Label(text='药品列表', font_size=16, bold=True))
        
        # 搜索框
        self.search_layout = BoxLayout(size_hint_y=None, height=dp(40))
        self.search_layout.add_widget(Label(text='搜索:'))
        self.search_input = TextInput(multiline=False)
        self.search_input.bind(text=self.search_medicines)
        self.search_layout.add_widget(self.search_input)
        self.list_frame.add_widget(self.search_layout)
        
        # 药品列表
        self.medicine_list = RecycleView()
        self.medicine_list.data = []
        self.medicine_list.viewclass = 'SelectableLabel'
        layout_manager = SelectableRecycleBoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        layout_manager.bind(minimum_height=layout_manager.setter('height'))
        self.medicine_list.add_widget(layout_manager)
        self.list_frame.add_widget(self.medicine_list)
        
        self.add_widget(self.list_frame)
        self.load_medicines()
    
    def update_layout(self, size):
        # 根据屏幕尺寸调整布局
        width, height = size
        
        if width < 600:  # 手机屏幕
            # 调整表单布局列数
            self.form_layout.cols = 2
            self.form_layout.height = dp(200)
            
            # 调整按钮布局为垂直
            self.button_layout.orientation = 'vertical'
            self.button_layout.height = dp(180)
            
            # 调整批量修改售价布局
            self.batch_frame.orientation = 'vertical'
            self.batch_frame.height = dp(80)
        else:  # 平板或更大屏幕
            # 调整表单布局列数
            self.form_layout.cols = 4
            self.form_layout.height = dp(100)
            
            # 调整按钮布局为水平
            self.button_layout.orientation = 'horizontal'
            self.button_layout.height = dp(50)
            
            # 调整批量修改售价布局
            self.batch_frame.orientation = 'horizontal'
            self.batch_frame.height = dp(40)
    
    def add_medicine(self, instance):
        # 实现添加药品的功能
        pass
    
    def clear_fields(self, instance):
        # 实现清空字段的功能
        pass
    
    def load_medicines(self, search_term=''):
        # 清空列表
        self.medicine_list.data = []
        
        # 加载药品数据
        if search_term:
            self.db.cursor.execute("SELECT pinyin, name, unit, price, sale_price FROM medicines WHERE name LIKE ? OR pinyin LIKE ?", 
                              (f"%{search_term}%", f"%{search_term.upper()}%"))
        else:
            self.db.cursor.execute("SELECT pinyin, name, unit, price, sale_price FROM medicines")
        medicines = self.db.cursor.fetchall()
        
        for medicine in medicines:
            medicine_info = f"{medicine[0]} - {medicine[1]} ({medicine[2]}) - 进价: {medicine[3]}元, 售价: {medicine[4]}元"
            self.medicine_list.data.append({'text': medicine_info, 'size_hint_y': None, 'height': dp(40)})
    
    def search_medicines(self, instance, value):
        self.load_medicines(value)
    
    def batch_update_sale_price(self, instance):
        # 实现批量修改售价的功能
        pass
    
    def import_from_excel(self, instance):
        # 实现从Excel导入的功能
        pass
    
    def download_template(self, instance):
        # 实现下载导入模板的功能
        pass
    
    def select_all(self, instance):
        # 实现全选功能
        pass
    
    def batch_delete(self, instance):
        # 实现批量删除功能
        pass

# 处方历史标签页
class HistoryTab(BoxLayout):
    def __init__(self, db, **kwargs):
        super(HistoryTab, self).__init__(**kwargs)
        self.db = db
        self.orientation = 'vertical'
        self.create_ui()
    
    def create_ui(self):
        # 处方历史列表
        self.list_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.list_frame.add_widget(Label(text='处方历史', font_size=16, bold=True))
        
        # 搜索框
        self.search_layout = BoxLayout(size_hint_y=None, height=dp(40))
        self.search_layout.add_widget(Label(text='搜索:'))
        self.search_input = TextInput(multiline=False)
        self.search_input.bind(text=self.search_prescriptions)
        self.search_layout.add_widget(self.search_input)
        self.list_frame.add_widget(self.search_layout)
        
        # 处方列表
        self.prescription_list = RecycleView()
        self.prescription_list.data = []
        self.prescription_list.viewclass = 'SelectableLabel'
        layout_manager = SelectableRecycleBoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        layout_manager.bind(minimum_height=layout_manager.setter('height'))
        self.prescription_list.add_widget(layout_manager)
        self.list_frame.add_widget(self.prescription_list)
        
        # 操作按钮
        self.button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=10)
        self.button_layout.add_widget(Button(text='查看详情', on_press=self.view_detail))
        self.button_layout.add_widget(Button(text='删除处方', on_press=self.delete_prescription))
        self.button_layout.add_widget(Button(text='导出Excel', on_press=self.export_excel))
        self.list_frame.add_widget(self.button_layout)
        
        self.add_widget(self.list_frame)
        self.load_prescriptions()
    
    def update_layout(self, size):
        # 根据屏幕尺寸调整布局
        width, height = size
        
        if width < 600:  # 手机屏幕
            # 调整按钮布局为垂直
            self.button_layout.orientation = 'vertical'
            self.button_layout.height = dp(120)
        else:  # 平板或更大屏幕
            # 调整按钮布局为水平
            self.button_layout.orientation = 'horizontal'
            self.button_layout.height = dp(50)
    
    def load_prescriptions(self, search_term=''):
        # 清空列表
        self.prescription_list.data = []
        
        # 加载处方数据
        if search_term:
            self.db.cursor.execute("""
            SELECT p.id, pa.name, p.diagnosis, p.date, p.total_price 
            FROM prescriptions p
            JOIN patients pa ON p.patient_id = pa.id
            WHERE pa.name LIKE ? OR p.diagnosis LIKE ?
            """, (f"%{search_term}%", f"%{search_term}%"))
        else:
            self.db.cursor.execute("""
            SELECT p.id, pa.name, p.diagnosis, p.date, p.total_price 
            FROM prescriptions p
            JOIN patients pa ON p.patient_id = pa.id
            """)
        prescriptions = self.db.cursor.fetchall()
        
        for prescription in prescriptions:
            prescription_info = f"ID: {prescription[0]}, 患者: {prescription[1]}, 诊断: {prescription[2]}, 日期: {prescription[3]}, 总金额: {prescription[4]}元"
            self.prescription_list.data.append({'text': prescription_info, 'size_hint_y': None, 'height': dp(40)})
    
    def search_prescriptions(self, instance, value):
        self.load_prescriptions(value)
    
    def view_detail(self, instance):
        # 实现查看详情的功能
        pass
    
    def delete_prescription(self, instance):
        # 实现删除处方的功能
        pass
    
    def export_excel(self, instance):
        # 实现导出Excel的功能
        pass

# 方剂模板标签页
class FormulaTab(BoxLayout):
    def __init__(self, db, **kwargs):
        super(FormulaTab, self).__init__(**kwargs)
        self.db = db
        self.orientation = 'vertical'
        self.create_ui()
    
    def create_ui(self):
        # 方剂模板输入
        self.input_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.input_frame.add_widget(Label(text='方剂模板输入', font_size=16, bold=True))
        
        # 表单布局
        self.form_layout = GridLayout(cols=1, spacing=10, size_hint_y=None, height=dp(200))
        
        self.form_layout.add_widget(Label(text='方剂名称:'))
        self.name_input = TextInput(multiline=False)
        self.form_layout.add_widget(self.name_input)
        
        self.form_layout.add_widget(Label(text='功效:'))
        self.description_input = TextInput(multiline=False)
        self.form_layout.add_widget(self.description_input)
        
        self.form_layout.add_widget(Label(text='组成:'))
        self.ingredients_input = TextInput(multiline=True)
        self.form_layout.add_widget(self.ingredients_input)
        
        self.input_frame.add_widget(self.form_layout)
        
        # 按钮布局
        self.button_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=10)
        self.button_layout.add_widget(Button(text='添加方剂', on_press=self.add_formula))
        self.button_layout.add_widget(Button(text='清空', on_press=self.clear_fields))
        self.button_layout.add_widget(Button(text='修改方剂', on_press=self.update_formula))
        self.button_layout.add_widget(Button(text='删除方剂', on_press=self.delete_formula))
        
        self.input_frame.add_widget(self.button_layout)
        self.add_widget(self.input_frame)
        
        # 方剂模板列表
        self.list_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.list_frame.add_widget(Label(text='方剂模板列表', font_size=16, bold=True))
        
        # 搜索框
        self.search_layout = BoxLayout(size_hint_y=None, height=dp(40))
        self.search_layout.add_widget(Label(text='搜索:'))
        self.search_input = TextInput(multiline=False)
        self.search_input.bind(text=self.search_formulas)
        self.search_layout.add_widget(self.search_input)
        self.list_frame.add_widget(self.search_layout)
        
        # 方剂列表
        self.formula_list = RecycleView()
        self.formula_list.data = []
        self.formula_list.viewclass = 'SelectableLabel'
        layout_manager = SelectableRecycleBoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        layout_manager.bind(minimum_height=layout_manager.setter('height'))
        self.formula_list.add_widget(layout_manager)
        self.list_frame.add_widget(self.formula_list)
        
        self.add_widget(self.list_frame)
        self.load_formulas()
    
    def update_layout(self, size):
        # 根据屏幕尺寸调整布局
        width, height = size
        
        if width < 600:  # 手机屏幕
            # 调整按钮布局为垂直
            self.button_layout.orientation = 'vertical'
            self.button_layout.height = dp(160)
        else:  # 平板或更大屏幕
            # 调整按钮布局为水平
            self.button_layout.orientation = 'horizontal'
            self.button_layout.height = dp(50)
    
    def add_formula(self, instance):
        # 实现添加方剂的功能
        pass
    
    def clear_fields(self, instance):
        # 实现清空字段的功能
        pass
    
    def load_formulas(self, search_term=''):
        # 清空列表
        self.formula_list.data = []
        
        # 加载方剂模板数据
        if search_term:
            self.db.cursor.execute("SELECT name, description, ingredients FROM formulas WHERE name LIKE ? OR description LIKE ?", 
                              (f"%{search_term}%", f"%{search_term}%"))
        else:
            self.db.cursor.execute("SELECT name, description, ingredients FROM formulas")
        formulas = self.db.cursor.fetchall()
        
        for formula in formulas:
            formula_info = f"{formula[0]} - {formula[1]}"
            self.formula_list.data.append({'text': formula_info, 'size_hint_y': None, 'height': dp(40)})
    
    def search_formulas(self, instance, value):
        self.load_formulas(value)
    
    def update_formula(self, instance):
        # 实现修改方剂的功能
        pass
    
    def delete_formula(self, instance):
        # 实现删除方剂的功能
        pass

# 设置标签页
class SettingsTab(BoxLayout):
    def __init__(self, db, **kwargs):
        super(SettingsTab, self).__init__(**kwargs)
        self.db = db
        self.orientation = 'vertical'
        self.create_ui()
    
    def create_ui(self):
        # 设置列表
        self.settings_frame = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.settings_frame.add_widget(Label(text='系统设置', font_size=16, bold=True))
        
        # 字体设置
        self.font_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.font_frame.add_widget(Label(text='字体大小:'))
        self.font_size_input = TextInput(multiline=False)
        self.font_frame.add_widget(self.font_size_input)
        self.settings_frame.add_widget(self.font_frame)
        
        # 字体类型
        self.font_family_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.font_family_frame.add_widget(Label(text='字体类型:'))
        self.font_family_input = TextInput(multiline=False)
        self.font_family_frame.add_widget(self.font_family_input)
        self.settings_frame.add_widget(self.font_family_frame)
        
        # 语言设置
        self.language_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.language_frame.add_widget(Label(text='语言:'))
        self.language_input = TextInput(multiline=False)
        self.language_frame.add_widget(self.language_input)
        self.settings_frame.add_widget(self.language_frame)
        
        # 用户名
        self.username_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.username_frame.add_widget(Label(text='用户名:'))
        self.username_input = TextInput(multiline=False)
        self.username_frame.add_widget(self.username_input)
        self.settings_frame.add_widget(self.username_frame)
        
        # 密码
        self.password_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.password_frame.add_widget(Label(text='密码:'))
        self.password_input = TextInput(multiline=False, password=True)
        self.password_frame.add_widget(self.password_input)
        self.settings_frame.add_widget(self.password_frame)
        
        # API密钥
        self.api_key_frame = BoxLayout(size_hint_y=None, height=dp(40))
        self.api_key_frame.add_widget(Label(text='DeepSeek API密钥:'))
        self.api_key_input = TextInput(multiline=False, password=True)
        self.api_key_frame.add_widget(self.api_key_input)
        self.settings_frame.add_widget(self.api_key_frame)
        
        # 保存按钮
        self.save_frame = BoxLayout(size_hint_y=None, height=dp(50))
        self.save_frame.add_widget(Button(text='保存设置', on_press=self.save_settings))
        self.settings_frame.add_widget(self.save_frame)
        
        self.add_widget(self.settings_frame)
        self.load_settings()
    
    def update_layout(self, size):
        # 根据屏幕尺寸调整布局
        width, height = size
        
        if width < 600:  # 手机屏幕
            # 调整各设置项的布局
            for frame in [self.font_frame, self.font_family_frame, self.language_frame, 
                         self.username_frame, self.password_frame, self.api_key_frame]:
                # 调整标签宽度
                for widget in frame.children:
                    if isinstance(widget, Label):
                        widget.size_hint_x = 0.3
                    elif isinstance(widget, TextInput):
                        widget.size_hint_x = 0.7
        else:  # 平板或更大屏幕
            # 恢复默认布局
            for frame in [self.font_frame, self.font_family_frame, self.language_frame, 
                         self.username_frame, self.password_frame, self.api_key_frame]:
                # 恢复默认尺寸
                for widget in frame.children:
                    widget.size_hint_x = None
    
    def load_settings(self):
        # 加载设置
        settings = {
            'font_size': '10',
            'font_family': 'SimHei',
            'language': 'zh_CN',
            'username': 'admin',
            'password': '123456',
            'deepseek_api_key': ''
        }
        
        for key in settings:
            self.db.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = self.db.cursor.fetchone()
            if result:
                settings[key] = result[0]
        
        self.font_size_input.text = settings['font_size']
        self.font_family_input.text = settings['font_family']
        self.language_input.text = settings['language']
        self.username_input.text = settings['username']
        self.password_input.text = settings['password']
        self.api_key_input.text = settings.get('deepseek_api_key', '')
    
    def save_settings(self, instance):
        # 保存设置
        settings = {
            'font_size': self.font_size_input.text,
            'font_family': self.font_family_input.text,
            'language': self.language_input.text,
            'username': self.username_input.text,
            'password': self.password_input.text,
            'deepseek_api_key': self.api_key_input.text
        }
        
        for key, value in settings.items():
            self.db.cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            ''', (key, value))
        
        self.db.conn.commit()
        self.show_popup('成功', '设置保存成功')
    
    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

if __name__ == '__main__':
    ChineseMedicinePrescriptionSystem().run()