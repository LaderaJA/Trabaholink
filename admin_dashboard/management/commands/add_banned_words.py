from django.core.management.base import BaseCommand
from admin_dashboard.models import ModeratedWord

class Command(BaseCommand):
    help = 'Add common Filipino and English profanity to banned words list'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing banned words before adding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            ModeratedWord.objects.filter(is_banned=True).delete()
            self.stdout.write(self.style.WARNING('Cleared all existing banned words'))

        # Comprehensive Filipino/Tagalog profanity and offensive words
        filipino_words = [
            # Core profanity
            'gago', 'gaga', 'gagong', 'gaguhan', 'kagaguhan',
            'putang', 'putangina', 'putanginamo', 'putanginang', 'putragis',
            'puta', 'pota', 'potah', 'punyeta', 'punyemas',
            'tangina', 'tanginamo', 'tanginang', 'tangena', 'taena',
            'tanga', 'tangahan', 'katangahan', 'tangang', 'tangal',
            'bobo', 'bobong', 'boba', 'kabobuhan', 'bobotante',
            
            # Insults and derogatory terms
            'ulol', 'ulo', 'loko', 'lokong', 'lukaret',
            'tarantado', 'tarantada', 'tarugo', 'taragis', 'taranta',
            'hinayupak', 'hayop', 'hayup', 'hayupak', 'hinayupang',
            'animal', 'animalya', 'animaling', 'animalito',
            'peste', 'pesteng', 'yawa', 'yawang', 'demonyo',
            'buwisit', 'bwiset', 'buset', 'buisit', 'bwesit',
            'leche', 'letse', 'letseng', 'lecheng', 'lechegas',
            'salbahe', 'salbaheng', 'salvaje', 'bastos', 'bastardo',
            
            # Sexual/crude terms
            'pokpok', 'pekpek', 'pepe', 'puki', 'puking',
            'titi', 'tite', 'titing', 'itlog', 'bayag',
            'kantot', 'kantutan', 'kantutin', 'kantutero', 'kantoterang',
            'chupa', 'chupaero', 'tsupa', 'supsupin', 'supsup',
            'jakol', 'jakolero', 'salsal', 'salsalin', 'salsalero',
            'tamod', 'tamodan', 'katas', 'katas', 'libog',
            'malibog', 'libogan', 'libugan', 'malupit', 'basura',
            'suso', 'dede', 'susong', 'teteng', 'pwet',
            'butas', 'bilat', 'birat', 'bruha', 'bruhang',
            
            # Variations and combinations
            'gagagohan', 'putahan', 'tangahan', 'bobuhan',
            'ulupong', 'lokong', 'pesteng yawa', 'leche puta',
            'putang yawa', 'yawang gago', 'gago ka', 'puta ka',
            'tangina mo', 'gago mo', 'putangina mo', 'ulol ka',
            'bobo ka', 'tanga ka', 'tarantado ka', 'peste ka',
            
            # Regional variations (Visayan/Bisaya)
            'yawa', 'yawaa', 'atay', 'atayka', 'piste',
            'pisteng yawa', 'lingin', 'lingaw', 'buang', 'buanga',
            'buogo', 'buogang', 'hinampak', 'luko', 'lukoa',
            'ungas', 'ungasa', 'ungoy', 'lubot', 'lubota',
            'bilat', 'bilata', 'utong', 'utonga', 'boto',
            'botbot', 'kinat', 'kinangkinang',
            
            # Ilocano profanity
            'agi', 'agida', 'ukininam', 'ukinam', 'uki',
            'bagtit', 'bagong', 'dakes', 'dakesa', 'maag',
            
            # Slang and street terms
            'kantutay', 'jepoy', 'jejemon', 'jologs', 'squatter',
            'squammy', 'skwater', 'iskwater', 'baduy', 'baduy-baduy',
            'jologs', 'jolagets', 'jejemon', 'jejebugs', 'jolog',
            'bakla', 'baklush', 'bayot', 'bayut', 'bading',
            'badingding', 'tomboy', 'tibo', 'lesbi', 'lesbiana',
            'sirena', 'shokot', 'shonga', 'shongaers', 'baluga',
            'baboy', 'babuyan', 'babi', 'buwaya', 'buwitre',
            'daga', 'bubwit', 'ipis', 'uod', 'higad',
            
            # Body shaming and discrimination
            'pangit', 'panget', 'pangeta', 'kapangitan', 'mukha',
            'mukhang', 'itim', 'ita', 'negra', 'negro',
            'intsik', 'tsekwa', 'bumbay', 'indian', 'kano',
            'tisoy', 'tisay', 'mestiso', 'mestisa', 'promdi',
            'probinsyano', 'bukid', 'bundok', 'barako', 'tambay',
            'tamad', 'walang', 'walanghiya', 'walang-hiya', 'sinungaling',
            
            # More insults and vulgar terms
            'lintik', 'kupal', 'kupalin', 'kupalpalan', 'shunga',
            'shungaers', 'shokot', 'shoket', 'shuket', 'shunga',
            'supot', 'supoting', 'taeng', 'dumi', 'ebak',
            'tae', 'taenga', 'jebs', 'jebsina', 'tarantadong',
            'inutil', 'inutel', 'walang kwenta', 'walang silbi',
            'hudas', 'hudasang', 'demonyo', 'demonyong', 'satanas',
            
            # Variants with Filipino morphology
            'gaguhan', 'putahan', 'tangahan', 'bobuhan', 'ulolan',
            'pestehen', 'lechehen', 'yawaon', 'gagawin', 'putahin',
            'tanginahin', 'boboin', 'ulolin', 'tarantadohin',
            'ginago', 'ginahasa', 'ginagago', 'pinagagago',
            'kinahampas', 'hinampas', 'hinayupan', 'kinaladkad',
            
            # Modern slang variations
            'gagi', 'gagiii', 'potacca', 'pucha', 'puchaaa',
            'anak ng', 'anakng', 'pakyu', 'pak u', 'fck',
            'amputa', 'amputek', 'tangek', 'tangnamo',
            'olol', 'ololol', 'ulul', 'ululin', 'awit',
            'aw', 'engot', 'engotero', 'giatay', 'gidemmet',
            
            # Combinations and creative spellings
            'p0ta', 'put@', 'g@go', 'g4go', 'b0b0',
            't4ng4', 'ul0l', 't4nt4d0', 'p3st3', 'l3ch3',
            'y4w4', 'p0kp0k', 'p0t4h', 'g4g1',
            'tangina nyo', 'putangina nyo', 'gago kayo', 'mga gago',
            'mga puta', 'mga tanga', 'mga bobo', 'mga ulol',
            
            # Additional vulgar terms
            'kantotero', 'kantoterang', 'tsupero', 'tsupaera',
            'jakolero', 'jakolera', 'salsalero', 'salsalera',
            'pumatay', 'mamatay', 'mamatay ka', 'sumama sa demonyo',
            'impyerno', 'masunog', 'mamatay sana', 'lumubog',
            'mahulog', 'masagasaan', 'madisgrasya', 'malunod',
            
            # More regional and dialectal profanity
            'gunggong', 'dungis', 'landas', 'lagalag', 'takas',
            'tukmol', 'tangkad', 'pandak', 'tabachoy', 'lurang',
            'ngiwi', 'bulag', 'pilay', 'pipi', 'bingi',
            'bungal', 'mangmang', 'ignorante', 'walang modo',
            'walang galang', 'bastusan', 'kabastusan', 'kalaswaan',
            
            # Street terms and gang slang
            'adik', 'adikan', 'batugan', 'batukan', 'bugaw',
            'bugawan', 'holdaper', 'snatcher', 'mandurukot', 'tulisan',
            'carnapper', 'rapist', 'manyak', 'manyakis', 'maniac',
            'sira', 'siraan', 'baliw', 'balawan', 'loka',
            
            # Additional derogatory terms
            'walanghiya', 'sinungaling', 'magnanakaw', 'kawatan',
            'salarin', 'kriminal', 'masamang tao', 'masama',
            'demonyo', 'kaaway', 'kalaban', 'traydor', 'taksil',
            'makasarili', 'sakim', 'madamot', 'kumag', 'hangal',
            
            # Insults about intelligence
            'tado', 'tadong', 'tonto', 'torpe', 'denghoy',
            'dengil', 'tangang', 'tontong', 'hardhead', 'tigas',
            'tigas ulo', 'kulit', 'makulit', 'pasaway', 'pasawayan',
            
            # More combinations
            'putanginang yan', 'putanginang to', 'leche kang',
            'gago ka talaga', 'tanga talaga', 'bobo talaga',
            'peste kang bata', 'leche ka', 'bwisit ka',
            'salot', 'salot ka', 'sakit ng ulo', 'sakit sa bangs',
        ]

        # Comprehensive English profanity
        english_words = [
            # Core profanity
            'fuck', 'fucking', 'fucker', 'fucked', 'fucks',
            'motherfucker', 'motherfucking', 'mothafucka', 'mofo',
            'shit', 'shitting', 'shitty', 'shithead', 'bullshit',
            'bitch', 'bitching', 'bitchy', 'bitches', 'son of a bitch',
            'asshole', 'ass', 'asses', 'jackass', 'dumbass',
            'bastard', 'bastards', 'bastardy',
            
            # Sexual terms
            'cock', 'cocks', 'dick', 'dicks', 'dickhead',
            'penis', 'vagina', 'pussy', 'pussies', 'cunt',
            'cunts', 'twat', 'whore', 'whores', 'slut',
            'sluts', 'hoe', 'hoes', 'hooker', 'prostitute',
            'rape', 'rapist', 'molest', 'molester',
            
            # Body parts and crude terms
            'tits', 'boobs', 'breasts', 'nipples', 'balls',
            'testicles', 'nuts', 'scrotum', 'anus', 'butthole',
            'butt', 'booty', 'fag', 'faggot', 'dyke',
            
            # Racial slurs
            'nigger', 'nigga', 'negro', 'chink', 'gook',
            'spic', 'wetback', 'beaner', 'cracker', 'honkey',
            'kike', 'jap', 'nip', 'towelhead', 'raghead',
            
            # More insults
            'idiot', 'idiots', 'moron', 'imbecile', 'retard',
            'retarded', 'stupid', 'dumb', 'dumbass', 'fool',
            'loser', 'losers', 'scum', 'scumbag', 'trash',
            'garbage', 'filth', 'pig', 'dog', 'animal',
            
            # Variations and creative spellings
            'fck', 'fuk', 'fuk', 'fvck', 'phuck',
            'sh1t', 'shyt', 'b1tch', 'bytch', 'azz',
            'a$$', 'a$$hole', 'd1ck', 'd!ck', 'fag',
            
            # Religious profanity
            'damn', 'damned', 'goddamn', 'goddamnit', 'hell',
            'hellish', 'jesus christ', 'christ', 'holy shit',
            
            # Additional vulgar terms
            'piss', 'pissed', 'pissing', 'crap', 'crappy',
            'suck', 'sucks', 'sucking', 'blow', 'blowjob',
            'handjob', 'jerk off', 'jerking', 'masturbate',
            'wank', 'wanker', 'jizz', 'cum', 'cumming',
            'orgasm', 'horny', 'sex', 'sexy', 'porn',
            'pornography', 'nude', 'naked', 'strip', 'stripper',
        ]

        all_words = filipino_words + english_words
        added_count = 0
        skipped_count = 0

        for word in all_words:
            obj, created = ModeratedWord.objects.get_or_create(
                word=word.lower(),
                defaults={'is_banned': True}
            )
            if created:
                added_count += 1
                self.stdout.write(self.style.SUCCESS(f'Added banned word: {word}'))
            else:
                skipped_count += 1
                if not obj.is_banned:
                    obj.is_banned = True
                    obj.save()
                    self.stdout.write(self.style.SUCCESS(f'Enabled banned word: {word}'))
                else:
                    self.stdout.write(f'Skipped existing word: {word}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: Added {added_count} words, Skipped {skipped_count} existing words'
            )
        )
