// Settings for the shared SEO head (same meaning as [params.seo] and [params.author] of the Hugo sites).
export const seo = {
  siteName: "JP-population-data",
  description: "日本政府・各省庁が公開する年齢別人口と自殺の統計を、出所と計算手順を明示して可視化した静的サイト。",
  locale: "ja_JP",
  language: "ja",
  image: "/ogp.png",
  imageWidth: 1200,
  imageHeight: 630,
  imageAlt: "JP-population-data のイメージ画像",
  twitterCard: "summary_large_image",
};

// A person's site: there is no publisher, only an author (shown as a Person in the JSON-LD).
export const author = {
  name: "椎名一霤",
  alternateName: ["シイナカズル", "Qajoule"],
  jobTitle: "Engineer | Explorer | Illustrator | Guitarist",
  sameAs: [
    "https://github.com/qajoule",
    "https://x.com/qajoule",
    "https://instagram.com/qajoule",
    "https://twitcasting.tv/qajoule",
  ],
};
