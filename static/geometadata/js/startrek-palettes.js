/**
 * Star Trek colour palettes from the trekcolors R package.
 * https://leonawicz.github.io/trekcolors/
 *
 * Palette hex codes extracted from:
 * https://github.com/leonawicz/trekcolors/blob/master/data-raw/data.R
 */
(function(window) {
    'use strict';

    window.STARTREK_PALETTES = {
        // Species/Faction palettes
        'starfleet': ['#5B1414', '#AD722C', '#1A6384'],
        'starfleet2': ['#5B1414', '#AD722C', '#1A6384', '#2C6B70', '#483A4A', '#000000'],
        'klingon': ['#000000', '#330000', '#660000', '#990000', '#CA0000', '#CA6400', '#C99400', '#FFFA0C'],
        'romulan': ['#1DF964', '#000000', '#429AFC'],
        'romulan2': ['#80F2B3', '#363636', '#30E1EA'],
        'andorian': ['#202020', '#446D99', '#83BDD7', '#E4E4E4'],
        'bajoran': ['#C00000', '#7A6424', '#323C34', '#4838A8', '#E6D56E', '#A8B5A9'],
        'borg': ['#1A1A1A', '#DDDDDD'],
        'breen': ['#56483D', '#332822', '#DFCDB9', '#996601', '#8BC95A', '#6C696F', '#F1E899', '#EE711E'],
        'breen2': ['#7E0500', '#CE1800', '#EF6F00', '#F7BD00', '#E4E4E4'],
        'dominion': ['#313131', '#255268', '#620062', '#63A542', '#A5C6D6', '#B5D6A5', '#B900B9'],
        'enara': ['#4D004D', '#800080', '#F46404', '#E7D057', '#E9E09C'],
        'enara2': ['#262626', '#3D5983', '#5A8A54', '#CFB023'],
        'ferengi': ['#00740E', '#E4E4E4', '#C86B32'],
        'gorn': ['#000042', '#0000B5', '#145416', '#639863', '#BDF7C6', '#FF0000', '#4E0000', '#A09349', '#777384'],
        'iconian': ['#633210', '#B85C1D', '#FFFFFF', '#6B666C'],
        'tholian': ['#5E0000', '#F07266', '#E1E1E1', '#D2C69C', '#9A7B08'],
        'terran': ['#000000', '#704D29', '#D4B293', '#D0CED1'],
        'ufp': ['#E4E4E4', '#201F7B'],

        // LCARS palettes (Library Computer Access and Retrieval System)
        'lcars_2357': ['#FFFF99', '#FFCC99', '#FFCC66', '#FF9933', '#664466', '#CC99CC', '#99CCFF', '#3366CC', '#006699'],
        'lcars_2369': ['#9999CC', '#9999FF', '#CC99CC', '#CC6699', '#CC6666', '#FF9966', '#FF9900', '#FFCC66'],
        'lcars_2375': ['#6688CC', '#4455BB', '#9977AA', '#774466', '#DD6644', '#AA5533', '#BB6622', '#EE9955'],
        'lcars_2379': ['#CCDDFF', '#5599FF', '#3366FF', '#0011EE', '#000088', '#BBAA55', '#BB4411', '#882211'],
        'lcars_alt': ['#FF9C00', '#F7BD5A', '#FFCC99', '#FFFF33', '#FFFF9C', '#CD6363', '#CC99CC', '#FF9E63', '#646DCC', '#9C9CFF', '#3399FF', '#99CCFF', '#FFFFCC', '#B1957A', '#ED884C', '#F5ED00', '#DDFFFF'],
        'lcars_first_contact': ['#C198B0', '#B46757', '#AE697D', '#97567B', '#C67825', '#B28452', '#C2B74B', '#BEBCDF'],
        'lcars_nemesis': ['#0A45EE', '#3786FF', '#4BB0FF', '#87EEFF', '#46616E', '#D45F10', '#A35A1A', '#A89B35', '#DFAF71', '#ACA98A'],
        'lcars_nx01': ['#BDEFFF', '#009CCE', '#DEFFB5', '#CD6363', '#E7FFFF', '#4D6184'],
        'lcars_29c': ['#39C924', '#72E2E4', '#20788C', '#24BEE2', '#BC956E', '#D19FA2', '#805070', '#2062EE'],
        'lcars_23c': ['#0000FF', '#99CCFF', '#6666FF', '#99FF66', '#009900', '#FF6633', '#66CCFF'],
        'lcars_red_alert': ['#F517C3', '#BF2D42', '#A30E24', '#330512', '#D9D5B8', '#F1DFBF', '#4C4D47', '#9E9993'],
        'lcars_cardassian': ['#B46356', '#944D40', '#7A4B42', '#CA480D', '#9B5928', '#C86C18', '#D78017', '#F9AB3C', '#FFE705', '#FFF7A3', '#E2ED50', '#2F7270', '#66FFFF', '#3C999C', '#8BEAFF', '#13A4EB', '#2E7BC5', '#A1B3E2', '#BFCAFE', '#8B799C', '#524559'],

        // Alert palettes
        'red_alert': ['#670000', '#990000', '#CD0000', '#FE0000', '#FF9190', '#4D4D4D'],
        'yellow_alert': ['#674305', '#986509', '#CD870E', '#FFA90E', '#FFDA67', '#4D4D4D'],
        'black_alert': ['#050B64', '#0E3A9B', '#307CE4', '#64FFFF', '#000000']
    };

    // Palette display names for UI
    window.STARTREK_PALETTE_LABELS = {
        // Species/Faction
        'starfleet': 'Starfleet',
        'starfleet2': 'Starfleet (Extended)',
        'klingon': 'Klingon Empire',
        'romulan': 'Romulan Star Empire',
        'romulan2': 'Romulan (Alt)',
        'andorian': 'Andorian',
        'bajoran': 'Bajoran',
        'borg': 'Borg Collective',
        'breen': 'Breen Confederacy',
        'breen2': 'Breen (Alt)',
        'dominion': 'Dominion',
        'enara': 'Enaran',
        'enara2': 'Enaran (Alt)',
        'ferengi': 'Ferengi Alliance',
        'gorn': 'Gorn Hegemony',
        'iconian': 'Iconian',
        'tholian': 'Tholian Assembly',
        'terran': 'Terran Empire',
        'ufp': 'United Federation of Planets',
        // LCARS
        'lcars_2357': 'LCARS 2357 (TNG Early)',
        'lcars_2369': 'LCARS 2369 (TNG/DS9)',
        'lcars_2375': 'LCARS 2375 (DS9 Late)',
        'lcars_2379': 'LCARS 2379 (Nemesis Era)',
        'lcars_alt': 'LCARS Alternative',
        'lcars_first_contact': 'LCARS First Contact',
        'lcars_nemesis': 'LCARS Nemesis',
        'lcars_nx01': 'LCARS NX-01 (Enterprise)',
        'lcars_29c': 'LCARS 29th Century',
        'lcars_23c': 'LCARS 23rd Century',
        'lcars_red_alert': 'LCARS Red Alert',
        'lcars_cardassian': 'LCARS Cardassian',
        // Alerts
        'red_alert': 'Red Alert',
        'yellow_alert': 'Yellow Alert',
        'black_alert': 'Black Alert (Discovery)'
    };

})(window);
