const got = require('got');
const cheerio = require('cheerio');
const { parseDate } = require('@/utils/parse-date');

/**
 * Example RSSHub Route for an Estate Agent
 * Location: /lib/v2/realestate/example-agent.js
 * 
 * This route scrapes an estate agent's list view, extracts all property URLs,
 * and uses ctx.cache.tryGet to visit each property page (only once!) to 
 * scrape the deep metadata required by the Daily Property Show Heart-Rate algorithm.
 */
module.exports = async (ctx) => {
    const rootUrl = 'https://www.example-estate-agent.com';
    const currentUrl = `${rootUrl}/properties-for-sale`;

    // 1. Fetch the listing page
    const response = await got({
        method: 'get',
        url: currentUrl,
    });
    const $ = cheerio.load(response.data);

    // 2. Extract property links from the list view
    const list = $('.property-grid .property-card').map((_, item) => {
        const title = $(item).find('.property-title').text().trim();
        const link = $(item).find('a').attr('href');
        return {
            title,
            link: link.startsWith('http') ? link : `${rootUrl}${link}`,
        };
    }).get();

    // 3. Visit each property page and extract detailed metadata
    // ctx.cache.tryGet ensures we don't hit the agent's site repeatedly for properties we've already cached
    const items = await Promise.all(
        list.map((item) =>
            ctx.cache.tryGet(item.link, async () => {
                const detailResponse = await got({
                    method: 'get',
                    url: item.link,
                });
                const content = cheerio.load(detailResponse.data);

                // Extract numerical and text data
                const priceText = content('.price-tag').text().replace(/[^0-9]/g, '');
                const beds = content('.features .beds').text().replace(/[^0-9]/g, '');
                const baths = content('.features .baths').text().replace(/[^0-9]/g, '');
                const location = content('.location-breadcrumb').text().trim();
                const description = content('.property-description').html();
                
                // Get all gallery images
                const images = content('.photo-gallery img').map((_, img) => {
                    let src = content(img).attr('src') || content(img).attr('data-src');
                    return `<img src="${src}" />`;
                }).get().join('\n');

                // Construct our standardized HTML payload for the RSSFeedIngester to parse
                item.description = `
                    <div class="metadata">
                        <span data-price="${priceText}">${content('.price-tag').text()}</span>
                        <span data-beds="${beds || 0}">${beds}</span>
                        <span data-baths="${baths || 0}">${baths}</span>
                        <span data-location="${location}">${location}</span>
                    </div>
                    <div class="description">
                        ${description}
                    </div>
                    <div class="gallery">
                        ${images}
                    </div>
                `;

                // Find the property ref ID and publication date (if available)
                item.guid = content('.ref-number').text().trim() || item.link;
                
                const dateText = content('.date-added').text();
                if (dateText) {
                    item.pubDate = parseDate(dateText);
                }

                return item;
            })
        )
    );

    // 4. Return the standardized feed
    ctx.state.data = {
        title: 'Example Estate Agent - For Sale',
        link: currentUrl,
        item: items,
    };
};
