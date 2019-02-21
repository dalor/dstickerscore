from dtelbot import Bot, inputmedia as inmed, reply_markup as repl, inlinequeryresult as iqr
from flask import Flask, request
import requests
from sticker_core import Dtelsticker
from PIL import Image
from io import BytesIO
import os
import re

BOT_ID = os.environ['BOT_ID']

HELP = '''Send me .png picture to simulate sticker.
<b>Editing stickers</b>
Reply /b OR /border with <i>style parameters</i> to get sticker with new border
<b>Border style language</b>
consist of 4 parts:
-<i>width</i> - the width of border in px (<b>Required</b>)
-<i>colour</i> - the colour of border in HEX OR rgb OR rgba (Not required: default is #ffffff OR rgb(255, 255, 255) OR rgba(255, 255, 255, 255))
-<i>position</i> - the coordinates of border position in px (Not required: default is (0, 0))
-<i>blur</i> - the radius of border`s blur (Not required: default is 0)
<b>Examples</b>
5 #ffff23 (-4, -4) 3
5 rgb(255, 255, 35) 3
5 (-4, -4) 3
5 3
5 rgba(255, 255, 35, 255) (-4, -4)
5 #ffff23
5'''

b = Bot(BOT_ID)

def load_pic(file_id, lib=True):
    pic_url = b.fileurl(file_id)
    response = requests.get(pic_url)
    with BytesIO(response.content) as bytes:
        pil_img = Image.open(bytes)
        return Dtelsticker(pil_img) if lib else pil_img

colours = {
    '#': {
        're': re.compile('([A-Fa-f\d]{6})'),
        'converter': lambda r: tuple(int(r[1][i:i + 2], 16) for i in (0, 2 ,4)) + (255, ) if r else None
    },
    'rgb': {
        're': re.compile('\(\s*(\d+)\s*\,\s*(\d+)\s*\,\s*(\d+)\s*\)'),
        'converter': lambda r: (int(r[1]), int(r[2]), int(r[3]), 255)
    },
    'rgba': {
        're': re.compile('\(\s*(\d+)\s*\,\s*(\d+)\s*\,\s*(\d+)\s*\,\s*(\d+)\s*\)'),
        'converter': lambda r: (int(r[1]), int(r[2]), int(r[3]), int(r[4]))
    }
}

def parse_colour(t, content):
    ctype = colours.get(t)
    if ctype:
        return ctype['converter'](ctype['re'].match(content))

border_parser = re.compile('(\d+)(px|)(\s*(rgba|rgb|#)(\([\d\,\s]+\)|[\d\w]+)|)(\s*\(?\s*([\-\d]+)(px|)\s*\,\s*([\-\d]+)(px|)\s*\)?|)(\s*(\d)+(px|)|)')

def border_args_to_text(args):
    return '<b>Border:</b> {}'.format(', '.join(filter(lambda x: x, [
        'width: {}'.format(args['width']),
        'colour: rgba{}'.format(args['colour']) if args['colour'] else None,
        'position: {}'.format(args['pos']) if args['pos'] else None,
        'blur: {}'.format(args['blur']) if args['blur'] else None
    ])))

def parse_border(text):
    res = border_parser.match(text)
    return {
        'width': int(res[1]),
        'colour': parse_colour(res[4], res[5]) if res[3] else None,
        'pos': (int(res[7]), int(res[9])) if res[6] else None,
        'blur': int(res[12]) if res[11] else None
    }
 
def send_sticker(pic, chat_id, reply_to_message_id=''):
    with BytesIO() as bytes:
        pic.save(bytes, format='WebP')
        bytes.seek(0)
        reply_markup = [[repl.inlinekeyboardbutton('Send', callback_data='send'), repl.inlinekeyboardbutton('Delete', callback_data='del')]]
        b.sticker(chat_id=chat_id, data={'sticker': bytes}, reply_markup=repl.inlinekeyboardmarkup(reply_markup), reply_to_message_id=reply_to_message_id).send()

@b.message('/start')
def start(a):
    a.msg('Hello!!!\nGo to /help').send()

@b.message('/help')
def help_msg(a):
    a.msg(HELP, parse_mode='HTML').send()

@b.edited_message('/(b|border) (.+)')
@b.message('/(b|border) (.+)')
def border(a):
    reply_message = a.data.get('reply_to_message')
    if reply_message:
        sticker = reply_message.get('sticker')
        if sticker:
            pic = load_pic(sticker['file_id'])
            args = parse_border(a.args[2])
            a.msg(border_args_to_text(args), parse_mode='HTML').send()
            pic = pic.border(
                args['width'],
                colour=args['colour'] if args['colour'] else (255, 255, 255, 255),
                pos=args['pos'] if args['pos'] else (0, 0),
                blur=args['blur'] if args['blur'] else 0
                )
            send_sticker(pic, a.data['chat']['id'], reply_to_message_id=a.data['message_id'])
            return
    a.msg('Reply me to sticker.').send()

@b.message(True)
def check_pic_(a):
    doc = a.data.get('document')
    sticker = a.data.get('sticker')
    if doc and doc['mime_type'].startswith('image'):
        if doc['mime_type'] != 'image/png':
            a.msg('I can make borders only for transparent pictures.').send()
        send_sticker(load_pic(doc['file_id']).sticker(), a.data['chat']['id'], reply_to_message_id=a.data['message_id'])
    elif sticker:
        pass
    else:
        a.msg('Send me .png picture as file').send()
        
@b.callback_query('send')
def send(a):
    sticker = a.data['message'].get('sticker')
    if sticker:
        with BytesIO() as bytes:
            load_pic(sticker['file_id'], False).save(bytes, format='PNG')
            bytes.seek(0)
            bytes.name = sticker['file_id'] + '.png'
            b.document(chat_id=a.data['message']['chat']['id'], data={'document': bytes}, reply_to_message_id=a.data['message']['message_id']).send()
            a.answer(text='Forward this file to @Stickers').send()
    else:
        a.answer(text='This is not sticker').send()

@b.callback_query('del')
def delete(a):
    b.delete(a.data['message']['message_id'], a.data['message']['chat']['id']).send()

app = Flask(__name__)

@app.route('/{}'.format(BOT_ID), methods=['POST']) #Telegram should be connected to this hook
def webhook():
    b.check(request.get_json())
    return 'ok', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
