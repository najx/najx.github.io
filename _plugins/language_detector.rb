# Language detection plugin for Jekyll
module LanguageEmoji
  # Strongly French-specific words (less ambiguous)
  FRENCH_WORDS = %w[
    le la les de du des et ou que qui comment pourquoi quand où qu
    est sont avoir être aller faire venir pouvoir devoir vouloir
    cependant donc ainsi bien ce qui
    pour par avec dans sur entre sous avant après
    jour mois année temps semaine aujourd'hui demain hier
    français france bonjour merci excusez s'il complètement
    bienvenue grâce réalité présent seulement jusqu'à depuis longtemps
    première deuxième troisième aucun chaque quelques plusieurs
    chercher trouver savoir croire penser sentir voir montrer
    l'homme l'existence vouloir peut faut fallait vont venez
    très rapidement lentement facile difficile possible impossible
    merveilleux horrible terrible fantastique extraordinaire magnifique
    oui non peut-être absolument certainement définitivement
    actuellement malheureusement heureusement finalement bref
    l'histoire l'aventure l'idée l'univers l'application
    rien quelque chose personne endroit place environ
    si alors mais car parce pourquoi comment quoi lequel
    visionnage vivement recommandé visionner regarder écouter entendre
    horreur existentiel angoisse crainte peur terreur effroi
  ].freeze

  def language_emoji(text, lang = nil)
    return text if text.nil? || text.strip.empty?
    
    # If language is explicitly provided via front-matter, use it
    if lang && (lang == 'fr' || lang == 'en')
      emoji = lang == 'fr' ? '🇫🇷' : '🇬🇧'
      return "#{emoji} #{text}"
    end
    
    text_lower = text.downcase
    words = text_lower.split
    french_count = 0

    FRENCH_WORDS.each do |word|
      french_count += words.count(word)
    end

    words_count = words.length
    # Require higher threshold: 8% of words must be French-specific to detect as French
    french_percentage = words_count > 0 ? (french_count.to_f / words_count) * 100 : 0

    emoji = french_percentage > 8 ? '🇫🇷' : '🇬🇧'
    "#{emoji} #{text}"
  end
end

Liquid::Template.register_filter(LanguageEmoji)
