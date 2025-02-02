from discord.ext import commands, tasks
from Logger import *
from discord import Embed
import datetime, mysql.connector

# Il faut lancer la commande 'loaduser' au démarage du bot pour charger les utilisateurs de la base de données.
class SchedulesCog(commands.Cog):

	REACTION = {
			"Amoureux":         "🥰",
			"Bonne journée":    "🙂",
			"Joyeux.se":        "😃",
			"Neutre":           "😐",
			"Déçu.e":           "😕",
			"Epuisé.e":         "😫",
			"Colérique":        "🤬",
			"Mauvaise journée": "🙁",
			"Zen":              "😌"
		}

	BUFFER = []
	HOUR = 19
	REGISTER = []
	REGISTER_ID = []
	LOGGER = Logger()
	NEXT_LOOP = []
	AUTHORIZATION_LAMBDA = False

	def __init__(self, bot, db):
		self.bot = bot
		self.db = db
		self.firstloop = True
		self.refaced()
		self.loaduser()

	def loaduser(self):
		sql = "SELECT * FROM users"
		self.dbCursor = self.db.cursor()
		self.dbCursor.execute(sql)
		# Clean storage
		SchedulesCog.REGISTER_ID.clear()
		# Initialize storage
		for user in self.dbCursor.fetchall():
			SchedulesCog.REGISTER.append([int(user[0]), user[1], user[2]])
			SchedulesCog.REGISTER_ID.append(int(user[0]))
		#DUMP
		print((str(len(SchedulesCog.REGISTER)) + " users load"))
		SchedulesCog.LOGGER.info((str(len(SchedulesCog.REGISTER)) + " users load"))

	def cog_unload(self):
		self.printer.cancel()

	@tasks.loop(seconds=5.0)
	async def printer(self):
		SchedulesCog.LOGGER.info("Ask Mood auto")
		if self.firstloop == False:
			await self.askme()
		else:
			self.firstloop = False
	
	@commands.command()
	async def authorizeAskme(self, ctx):
		""" Permet à l'administrateur d'autoriser les demandes utilisateurs askme manuelle sur soi-même uniquement. """
		if ctx.author.id == 176264765214162944:
			print("Demande manuelle autorisé pour les utilisateurs.")
			SchedulesCog.AUTHORIZATION_LAMBDA = not SchedulesCog.AUTHORIZATION_LAMBDA

	@commands.command()
	async def ask(self, ctx):
		if ctx.author.id == 176264765214162944:
			print("Demande manuelle")
			SchedulesCog.LOGGER.info("Demande de Mood manuelle")
			await self.askme()
		elif(SchedulesCog.AUTHORIZATION_LAMBDA):
			await self.askme(ctx)
		else:
			await ctx.send("Tu n'as pas la permission de faire cette commande. Désolé !")

	async def askme(self, ctx=None):
		_ctx = None or ctx
		embed = Embed(title="How are you ?", color=0xe80005, timestamp=datetime.datetime.today())
		# Adding all the emoji in REACTION
		# TODO : Create an mood object containing every information about the processing 
		for mood, emoji in SchedulesCog.REACTION.items():
			embed.add_field(name=mood, value=emoji, inline=True)
		# Check if register match bdd users and get it if doesn't match
		if _ctx:
			message = await _ctx.author.send(embed=embed)
			SchedulesCog.BUFFER.append(message.id)
			await self.set_reaction(message)
		else:
			for user in SchedulesCog.REGISTER:
				if user[2] == 1:
					user_discord = await self.bot.fetch_user(user[0])

					if user_discord:
						message = await user_discord.send(embed=embed)
						SchedulesCog.BUFFER.append(message.id)
						await self.set_reaction(message)

			self.printer.change_interval(hours=24)

	@commands.command(help="Vous inscrit au processus")
	async def submood(self, ctx):
		SchedulesCog.LOGGER.info({ctx.author.id} + " s'inscrit du processus")

		if ctx.author.id in SchedulesCog.REGISTER_ID and SchedulesCog.REGISTER[SchedulesCog.REGISTER_ID.index(ctx.author.id)][2] != 1:
			await self.updateSubUser(ctx)
		elif ctx.author.id in SchedulesCog.REGISTER_ID:
			await ctx.send("Tu es déjà inscrit à la demande de Mood quotidienne.")
		else:
			await self.addSubUser(ctx)

	async def updateSubUser(self, ctx):
		await ctx.send("*Je te connait toi non ?*\nTu viens de t'inscrire à la demande de Mood.\n Cette question te sera posée tous les jours à 19h00 (GMT+1)")
		sql = f"UPDATE users SET mood_Sub = 1 WHERE id_Discord = {ctx.author.id}"
		self.dbCursor = self.db.cursor()
		self.dbCursor.execute(sql)
		self.db.commit()
		if((index := SchedulesCog.REGISTER_ID.index(ctx.author.id))):
			SchedulesCog.REGISTER[index][2] = 1
		print(self.dbCursor.rowcount, "record(s) affected")

	async def addSubUser(self, ctx):
		await ctx.send("*On ne se connait pas encore il me semble* ?\nTu viens de t'inscrire à la demande de Mood.\n Cette question te sera posée tous les jours à 19h30 (GMT+1)")
		sql = "INSERT INTO users (id_Discord, birthday_Sub, mood_Sub) VALUES (%s, %s, %s);"
		val = (str(ctx.author.id), 0, 1)
		self.dbCursor = self.db.cursor()
		self.dbCursor.execute(sql, val)
		self.db.commit()
		SchedulesCog.REGISTER_ID.append(ctx.author.id)
		SchedulesCog.REGISTER.append([ctx.author.id, 0, 1])
		print(self.dbCursor.rowcount, "record(s) affected")

	@commands.command(help="Vous désinscrit du processus")
	async def unsubmood(self, ctx):
		SchedulesCog.LOGGER.info(str(ctx.author.id) + " se désinscrit du processus")
		# Check if Author was actually registered, and active
		if ctx.author.id in SchedulesCog.REGISTER_ID and SchedulesCog.REGISTER[SchedulesCog.REGISTER_ID.index(ctx.author.id)][2] == 1:
			sql = f"UPDATE users SET mood_Sub = 0 WHERE id_Discord = {ctx.author.id}"
			self.dbCursor = self.db.cursor()
			self.dbCursor.execute(sql)
			self.db.commit()
			SchedulesCog.REGISTER[SchedulesCog.REGISTER_ID.index(ctx.author.id)][2] = 0
			#DUMP
			print(self.dbCursor.rowcount, "record(s) affected")
			await ctx.message.reply(f"Vous venez de vous désinscrire du processus de Mood :cry:\n Vous pouvez toujours vous réinscrire avec la commande {self.bot.command_prefix}submood !")

	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		if reaction.message.id in SchedulesCog.BUFFER and not user.bot and user.id in SchedulesCog.REGISTER_ID:
			# Checking 
			emoji = reaction.emoji
			date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			if ((emoj := self.check_emoji(emoji)) == None):
				await reaction.message.channel.send("Tu as utiliser une emoji qui n'est pas encore disponible.")
			# Stocker le mood de la personne
			sql = "INSERT INTO mood VALUES (%s, %s, %s);"
			val = (user.id, emoj, date)
			self.dbCursor = self.db.cursor()
			self.dbCursor.execute(sql, val)
			self.db.commit()
			print(self.dbCursor.rowcount, "record(s) affected")
			# Reply with information then delete embed to keep the feed clean
			await reaction.message.reply("Ton mood a était prit en compte. Merci !")
			await reaction.message.delete()

	def refaced(self):
		_hour = SchedulesCog.HOUR
		# Generating date for the next call
		next_call = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
		next_call = next_call.replace(hour=_hour, minute=0, second=0)
		delta = self.time_until(next_call)  
		# Change interval will only take action at the next loop
		try:
			SchedulesCog.LOGGER.info("Prochaine loop " + str(delta))
			self.printer.change_interval(seconds=delta)
			self.printer.start()
			SchedulesCog.NEXT_LOOP.append(["mood", datetime.datetime.now(), delta])
		except Exception as e:
			print(e)

	@commands.command(help="Affiche l'heure de la prochaine demande de Mood")
	async def nextLoop(self, ctx):
		next_call = datetime.datetime.now() + datetime.timedelta(seconds=SchedulesCog.NEXT_LOOP[0][2])
		SchedulesCog.LOGGER.info("Next iteration: " + str(next_call.strftime("%d-%m-%Y à %H:%M:%S")))
		await ctx.message.reply("Prochaine demande de Mood le : " + str(next_call.strftime("%d-%m-%Y à %H:%M:%S")))

	def time_until(self, when) -> float:
		if when.tzinfo is None:
			when = when.replace(tzinfo=datetime.timezone.utc)
		now = datetime.datetime.now(datetime.timezone.utc)
		delta = (when - now).total_seconds()
		return delta

	async def set_reaction(self, message):
		for emoji in SchedulesCog.REACTION.values():
			await message.add_reaction(emoji)

	def check_emoji(self, em):
		for reaction in SchedulesCog.REACTION:
			if em == SchedulesCog.REACTION[reaction]:
				return reaction
		
	@commands.command(pass_context = True, help="va vous donner les commandes concernant le processus de Mood !")
	async def moodinfo(self, ctx):
		await ctx.message.reply("L'expérience Mood a pour but de vous demander votre état sur la journée à 19h00 (GMT+1)\n"
		+ "```md\n"
		+ "#Commandes Mood\n"
		+ f"- submood : Vous inscrit au processus\n"
		+ f"- unsubmood : Vous désinscrit du processus\n"
		+ f"- moodinfo : Montre ce message"
		+ f"- rgpd : Donne des informations sur la rgpd"
		+ "\n#Commandes à venir\n"
		+ f"- recap : Vous donne un récapitulatif de votre mood. (La façon de transmettre le récap n\'est pas encore déterminé\n"
		+ "```")
		
	@commands.command(help="La RGPD c'est quoi ?")
	async def rgpd(self, ctx):
		await ctx.message.reply("Hum... RGPD, c'est à propos de vos données. Des infos ici https://www.cnil.fr/fr/comprendre-le-rgpd\n\n Comment dire que vos données avec moi, Marie-Louise d'Autriche, elles sont stockées dans mon coffre et je ne les vends pas."
		+ "Il y a surement moyen que je fasse des stats ou d'autres truc un jour avec mais jamais je ne ferais d'argent avec. Don\'t worry\n Si vous voulez tout de même supprimer vos données, faite signe à Dronai#2906 et il fera le nécessaire !"
		+ "\n\n PS: Je stock votre mood à chaque fois que vous l'indiquez et votre ID Discord.")

	@commands.command(help="donne un récapitulatif de votre mood")
	async def recap(self, ctx):
		await ctx.send("Cette fonctionnalitée n'est pas encore disponible.")