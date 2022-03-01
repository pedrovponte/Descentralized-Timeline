import asyncio

class Menu:
    def __init__(self, name, notifications):
        self.name = name
        self.notifications = notifications
        self.searchedUser = None
        self.items = []
        self.option = -1

    def append_item(self, item):
        self.items.append(item)

    def print_menu(self):
        nr = int((79 - len(self.name) - 2)/2)
        if (nr * 2 + len(self.name) + 2) != 79:
            print("=" * nr + " " + self.name + " " + "=" * (nr + 1))
        else:
            print("=" * nr + " " + self.name + " " + "=" * nr)

        if self.notifications:
            print("| |" + "‾"*73 + "| |")
            print("| |" + " "* 28 + "NEW NOTIFICATIONS" + " " * 28 + "| |")
            print("| |" + " "*73 + "| |")
            for n in self.notifications:
                size = int((73-len(n[0]))/2)
                if len(n[0])%2 == 0:
                    print("| |" + " "*(size + 1) + n[0] + " "*size + "| |")
                else:
                    print("| |" + " "*size + n[0] + " "*size + "| |")
            print("| |" + "_"*73 + "| |")
            print("|" + " "*77 + "|")

        if self.searchedUser is not None:
            username = "| User info: " + str(self.searchedUser[0])
            if self.searchedUser[1]['online']:
                username = username + " (currently online)"
            else:
                username = username + " (currently offline)"
            print(username + (77 - len(username)) * " " + " |")
            print("|" + 77 * " " + "|")

        option = 1
        for item in self.items:
            spaces = 79 - 6 - len(str(option)) - len(item.get_name())
            print("| " + str(option) + ": " + item.get_name() +
                  spaces * " " + " |")
            option += 1

        print("=" * 79)

    def execute(self):
        while(self.option == -1):
            self.print_menu()
            self.read_option()

            if self.option != -1 and self.option <= len(self.items):
                op = self.option
                self.option = -1
                return self.items[op - 1].run()

    def read_option(self):
        option = input("> ")
        try:
            if int(option) <= 0 or int(option) > len(self.items):
                self.option = -1
                print("Escolhida opção inválida!")
            else:
                self.option = int(option)
        except ValueError:
            self.option = -1
            print("Opção deve ser numérica!")

    def addConstLine(self, searchedUser):
        self.searchedUser = searchedUser
