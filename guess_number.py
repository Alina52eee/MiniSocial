import random


def guess_number_game():
    print("Добро пожаловать в игру 'Угадай число'!")
    print("Я загадал число от 1 до 100.")

    secret_number = random.randint(1, 100)
    attempts = 0

    while True:
        user_input = input("Введите ваше число: ")

        if not user_input.isdigit():
            print("Пожалуйста, введите целое число.")
            continue

        guess = int(user_input)
        attempts += 1

        if guess < secret_number:
            print("Слишком маленькое число!")
        elif guess > secret_number:
            print("Слишком большое число!")
        else:
            print(f"Поздравляю! Вы угадали число {secret_number} за {attempts} попыток.")
            break


if __name__ == "__main__":
    guess_number_game()
