<template>
    <div>
        <div :style="customStyle" v-html="rawHtmlContent"/>
    </div>
</template>

<script>
export default {
    name: "ElementsFromHTML",
    data: function () {
        return {
            rawHtmlContent: "",
        };
    },
    props: {
        rawHtmlURL: {
            type: String,
            required: true,
        },
        customStyle: {
            type: String,
            default: "",
        },
    },
    methods: {
        readAndParseHTML(htmlUrl) {
            fetch(htmlUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.text(); // Extract the text body from the response
                })
                .then(html => {
                    const body = this.extractBody(html);
                    this.rawHtmlContent = body;
                })
                .catch(error => {
                    console.error('There was a problem with the fetch operation:', error);
                });      
            return
        },
        extractBody(htmlText) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlText, "text/html");
            const body = doc.body;
            return body.innerHTML; // Returns the inner HTML of the <body> element
        },
    },
    beforeRouteUpdate(to, from, next) {
        // This is needed for authorization when changing from one iFrame window to another.
        // Since this happens on the same route, beforeRoute navigation guards are not triggered.
        return guardRoute(to, from, next);
    },
    watch: {
        rawHtmlURL: {
            immediate: true, 
            handler (val, oldVal) {
                // do your stuff
                if (val != oldVal) {
                    this.readAndParseHTML(this.rawHtmlURL);
                }
            },
        }
    }
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped lang="scss">
.no-border {
    border: none;
}
</style>