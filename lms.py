import json
import os
import requests
import telegram
from dotenv import load_dotenv
from time import sleep
from datetime import date

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
EXPECTED_MONTH_PROFIT = 8
EPIC_ZERO_PRICE = 3
LEG_ZERO_PRICE = 35
EPIC_DAILY_INCOME = 0.5
LEG_DAILY_INCOME = 1.25
PRICE_MAX_EPIC = 30
PRICE_MAX_LEG = 50


def send_message(message):
    """Send message to tg"""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except telegram.TelegramError:
        raise telegram.TelegramError('Error tg message')


def get_data(page, rarity, price_max):
    retries = 0
    success = 0
    while retries <= 3 and success == 0:
        try:
            res = requests.get(
                f'https://api-crypto.letmespeak.org/api/escrow?priceMin=1'
                f'&priceMax={price_max}&visaLeftMin=3&visaLeftMax=240'
                f'&rarity={rarity}&page={page}&sortBy=LowestPrice'
            )
            res_dict = json.loads(res.text)
            success = 1
            return res_dict.get('items')
        except:
            sleep(5)
            retries += 1

    return 'get_data error'


def get_all_data(rarity, price_max):
    res = []
    page = 1
    data = get_data(page, rarity, price_max)
    if data == 'get_data error':
        return 'get_data error'
    while data:
        res += data
        page += 1
        data = get_data(page, rarity, price_max)
        sleep(1)

    return res


def check_and_save_good_nft(good_nft):
    with open('lms.txt', 'r') as f:
        existing_nfts = f.read().splitlines()

    good_nft_unic = []
    for item in good_nft:
        if json.dumps(item) not in existing_nfts:
            good_nft_unic.append(item)

    good_nft_unic_str = '\n'.join([json.dumps(x) for x in good_nft_unic])

    with open('lms.txt', 'a') as f:
        if good_nft_unic_str:
            f.write(str(date.today()) + '\n' + good_nft_unic_str + '\n')

    return good_nft_unic_str


def get_good_nft(nfts, rarity):
    good_nft = []
    for nft in nfts:
        visa_left = nft.get('properties').get('visaLeft')
        price = nft.get('price')
        if rarity == 4:
            daily_income = EPIC_DAILY_INCOME
            zero_price = EPIC_ZERO_PRICE
        elif rarity == 5:
            daily_income = LEG_DAILY_INCOME
            zero_price = LEG_ZERO_PRICE
        else:
            raise ValueError('Invalid value: rarity')
        profit = visa_left * daily_income + zero_price - price
        roi = round(profit / price * 100, 2)
        month_profit = round(30 * profit / visa_left, 2)
        if month_profit >= EXPECTED_MONTH_PROFIT:
            good_nft.append({
                'link': 'https://market.letmespeak.org/escrow/' + nft.get('id'),
                'price': price, 'profit': profit, 'visa': visa_left,
                'roi': roi, 'month_profit': month_profit
            })

    if good_nft:
        # for sort
        def get_month_profit(elem):
            return elem.get('month_profit')

        good_nft_sorted = sorted(good_nft, key=get_month_profit, reverse=True)
        good_nft_unic_str = check_and_save_good_nft(good_nft_sorted)

        return good_nft_unic_str

    return None


def main():
    nfts_epic = get_all_data(rarity=4, price_max=PRICE_MAX_EPIC)
    if nfts_epic == 'get_data error':
        good_nft_epic = 'get_data error'
    else:
        good_nft_epic = get_good_nft(nfts_epic, rarity=4)

    nfts_leg = get_all_data(rarity=5, price_max=PRICE_MAX_LEG)
    if nfts_leg == 'get_data error':
        good_nft_leg = 'get_data error'
    else:
        good_nft_leg = get_good_nft(nfts_leg, rarity=5)

    if good_nft_epic or good_nft_leg:
        message = (
            f'Something interesting has come up\n\n'
            f'Epic:\n{good_nft_epic}\n\n'
            f'Legendary:\n{good_nft_leg}'
        )
        send_message(message)


if __name__ == '__main__':
    main()
