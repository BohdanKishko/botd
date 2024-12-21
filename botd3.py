import discord
import re
import os
import logging

# Налаштування логування
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('discord')

intents = discord.Intents.default()
intents.members = True  
intents.guilds = True  # Необхідно для створення каналів
client = discord.Client(intents=intents)

# Замініть 'ПостійнаРоль' на назву ролі, яку ви хочете видавати
PERMANENT_ROLE_NAME = 'СТК'  # або отримуйте через os.environ.get('PERMANENT_ROLE_NAME', 'ПостійнаРоль')

@client.event
async def on_ready():
    print(f'Бот {client.user} увійшов в систему')
    await setup_welcome_channel(client.guilds[0])  # Застосовуємо на першому сервері, змініть індекс, якщо потрібно

async def setup_welcome_channel(guild):
    # Створюємо роль для нових користувачів
    new_member_role = discord.utils.get(guild.roles, name="Новачок")
    if not new_member_role:
        new_member_role = await guild.create_role(name="Новачок", permissions=discord.Permissions(0), colour=discord.Colour.blue())
    
    # Знаходимо або створюємо постійну роль
    permanent_role = discord.utils.get(guild.roles, name=PERMANENT_ROLE_NAME)
    if not permanent_role:
        permanent_role = await guild.create_role(name=PERMANENT_ROLE_NAME, permissions=discord.Permissions(read_messages=True), colour=discord.Colour.green())
    
    # Перевіряємо, чи існує канал "welcome", і створюємо, якщо ні
    welcome_channel = discord.utils.get(guild.text_channels, name="welcome")
    if not welcome_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
            new_member_role: discord.PermissionOverwrite(read_messages=True)
        }
        welcome_channel = await guild.create_text_channel("welcome", overwrites=overwrites)
    
    # Зберігаємо інформацію про канал, тимчасову та постійну ролі
    client.welcome_channel = welcome_channel
    client.new_member_role = new_member_role
    client.permanent_role = permanent_role

@client.event
async def on_member_join(member):
    guild = member.guild
    if hasattr(client, 'welcome_channel') and hasattr(client, 'new_member_role') and hasattr(client, 'permanent_role'):
        try:
            await member.add_roles(client.new_member_role)
            print(f'Роль {client.new_member_role.name} видана {member.name}')

            class NicknameButton(discord.ui.View):
                def __init__(self, *, timeout=180):
                    super().__init__(timeout=timeout)
                    self.add_item(discord.ui.Button(label="Введіть нікнейм", style=discord.ButtonStyle.primary, custom_id="nickname_modal"))
                    logger.debug(f"Number of components in view: {len(self.children)}")

                async def interaction_check(self, interaction: discord.Interaction):
                    if interaction.user == member:
                        modal = NicknameModal(member, message)  # Передаємо повідомлення до модалі для подальшого видалення
                        logger.debug(f"Number of components in modal before sending: {len(modal.children)}")
                        await interaction.response.send_modal(modal)
                        return False  # Забороняємо повторну взаємодію з кнопкою
                    else:
                        await interaction.response.send_message("Це повідомлення не для вас!", ephemeral=True)
                        return False

            class NicknameModal(discord.ui.Modal, title="Введіть ваш нікнейм, ім'я та сервер"):
                def __init__(self, user, message):
                    super().__init__()
                    self.user = user
                    self.message = message  # Зберігаємо повідомлення для видалення
                    self.nickname = discord.ui.TextInput(label="Нікнейм у грі", style=discord.TextStyle.short, placeholder="Введіть ваш нікнейм тут, як Nick_Name")
                    self.real_name = discord.ui.TextInput(label="Своє ім'я (укр/англ/рос)", style=discord.TextStyle.short, placeholder="Введіть ваше ім'я")
                    self.server_number = discord.ui.TextInput(label="Номер сервера", style=discord.TextStyle.short, placeholder="Введіть номер вашого сервера")
                    self.add_item(self.nickname)
                    self.add_item(self.real_name)
                    self.add_item(self.server_number)
                    logger.debug(f"Number of components in modal: {len(self.children)}")

                async def on_submit(self, interaction: discord.Interaction):
                    new_nickname = self.nickname.value
                    real_name = self.real_name.value
                    server_number = self.server_number.value

                    formatted_nickname = f"{new_nickname}[{real_name}][{server_number}]"

                    if re.match(r'^[A-Za-z]+_[A-Za-z]+\[[A-Za-zа-яА-ЯёЁіІїЇєЄґҐ\s]+\]\[[0-9]+\]$', formatted_nickname):
                        try:
                            await self.user.edit(nick=formatted_nickname)
                            await interaction.response.send_message(f"Ваш нікнейм у грі змінено на: {formatted_nickname}", ephemeral=True)
                            # Видаляємо тимчасову роль "Новачок" і додаємо постійну роль
                            await self.user.remove_roles(client.new_member_role)
                            await self.user.add_roles(client.permanent_role)
                            print(f'Постійна роль {client.permanent_role.name} додана {self.user.name}')
                            # Видаляємо повідомлення після видачі постійної ролі
                            await self.message.delete()
                        except discord.errors.Forbidden:
                            await interaction.response.send_message("У бота немає прав для зміни вашого нікнейму або видачі ролей.", ephemeral=True)
                        except discord.errors.HTTPException as e:
                            await interaction.response.send_message(f"Сталася помилка при зміні нікнейму або видачі ролей: {str(e)}", ephemeral=True)
                    else:
                        await interaction.response.send_message("Нікнейм повинен бути у форматі Nick_Name[Ім'я][Номер сервера].\nНік: англійські букви і '_', Ім'я: букви будь-якої з мов, Номер: цифри.", ephemeral=True)

            # Відправляємо повідомлення в канал "welcome"
            message = await client.welcome_channel.send(f"Добро пожаловать, {member.mention}! Пожалуйста, нажмите кнопку для ввода вашего никнейма в игре:", view=NicknameButton())

        except Exception as e:
            logger.error(f"Виникла помилка при обробці нового користувача: {type(e).__name__} - {str(e)}")

client.run('MTMyMDA1MDE5NTc0NDAzMDc4MA.GHh6e2.uXZPStyufPKJm5TVZfl4Ka2ks2GIQxANgEzysc')  # Не забудьте замінити на ваш реальний токен бота
