import json
import os
import requests
import telegram
from dotenv import load_dotenv
from time import sleep

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
EXPECTED_MONTH_PROFIT = 8
ZERO_PRICE = 3
EPIC_DAILY_INCOME = 0.5
LEG_DAILY_INCOME = 1.25
PRICE_MAX_EPIC = 30
PRICE_MAX_LEG = 40


def get_data(page, rarity, price_max):
    res = requests.get(
        f'https://api-crypto.letmespeak.org/api/escrow?priceMin=1'
        f'&priceMax={price_max}&visaLeftMin=3&visaLeftMax=240&rarity={rarity}'
        f'&page={page}&sortBy=LowestPrice'
    )
    res_dict = json.loads(res.text)

    return res_dict.get('items')


def send_message(bot, message):
    """Send message to tg"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except telegram.TelegramError:
        raise telegram.TelegramError('Error tg message')


def get_all_data(rarity, price_max):
    res = []
    page = 1
    data = get_data(page, rarity, price_max)
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
            f.write(good_nft_unic_str + '\n')

    return good_nft_unic_str


def get_good_nft(nfts, rarity):
    good_nft = []
    for nft in nfts:
        visaLeft = nft.get('properties').get('visaLeft')
        price = nft.get('price')
        if rarity == 4:
            daily_income = EPIC_DAILY_INCOME
        elif rarity == 5:
            daily_income = LEG_DAILY_INCOME
        else:
            raise ValueError('Invalid value: rarity')
        profit = visaLeft * daily_income + ZERO_PRICE - price
        roi = round(profit / price * 100, 2)
        month_profit = round(30 * profit / visaLeft, 2)
        if month_profit >= EXPECTED_MONTH_PROFIT:
            good_nft.append({
                'link': 'https://market.letmespeak.org/escrow/' + nft.get('id'),
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
    good_nft_epic = get_good_nft(nfts_epic, rarity=4)

    nfts_leg = get_all_data(rarity=5, price_max=PRICE_MAX_LEG)
    good_nft_leg = get_good_nft(nfts_leg, rarity=5)

    if good_nft_epic or good_nft_leg:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        message = (
            f'Something interesting has come up\n\n'
            f'Epic:\n{good_nft_epic}\n\n'
            f'Legendary:\n{good_nft_leg}'
        )
        send_message(bot, message)


if __name__ == '__main__':
    main()
