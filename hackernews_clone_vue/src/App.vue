<template>
  <div :class="$style.container">
    <div :class="$style.taskInfo">
      <update-box
        style="grid-area: apiUpdateBox"
        :updateUrl="apiBoxUpdateUrl"
        :refreshUrl="apiBoxRefreshUrl">
        Update Using API
      </update-box>
      <update-box
        style="grid-area: scrapperUpdateBox"
        :updateUrl="scrapperBoxUpdateUrl"
        :refreshUrl="scrapperBoxRefreshUrl">
        Update Using Scapper
      </update-box>
    </div>
    <div :class="$style.header">
      <div>
        <span 
          @click="loadPosts(url, true)"
          :class="$style.headerTitle">
          Hacker News Clone
        </span>
        By <a href="https://www.linkedin.com/in/yusufertekin">Yusuf Ertekin</a>
      </div>
      <div :class="$style.headerGroup">
        <input
          :class="$style.search"
          v-model="search"
          @change="searchPosts()"
          placeholder="Search">
      </div>
    </div>
    <div :class="$style.content">
      <div v-if="!fetchingActive" class="flexCol">
        <post-box
          v-for="post in posts"
          :key="post.id"
          :post="post">
        </post-box>
      </div>
      <span v-else :class="$style.message">Update with Hackernews in progress</span>
    </div>
    <div :class="$style.footer">
      <div>
        By <a href="https://www.linkedin.com/in/yusufertekin">Yusuf Ertekin</a>
      </div>
    </div>
  </div>
</template>

<script>
  import debounce from 'lodash/debounce';
  import PostBox from './components/PostBox.vue';
  import UpdateBox from './components/UpdateBox.vue';

  const apiHostUrl = __API_HOST_URL__;
  
  export default {
    components: {
      PostBox,
      UpdateBox,
    },

    data () {
      return {
        posts: [],
        url: `${apiHostUrl}posts/`,
        refreshIntervalId: null,
        search: null,
        nextUrl: null,
      }
    },
    
    computed: {
      fetchingActive() {
        return this.$store.getters.fetchingActive;
      },
      apiBoxUpdateUrl() {
        return `${apiHostUrl}posts/update-using-api/`;
      },
      apiBoxRefreshUrl() {
        return `${apiHostUrl}posts/get-fetch-api-info/`;
      },
      scrapperBoxUpdateUrl() {
        return `${apiHostUrl}posts/update-using-scrapper/`;
      },
      scrapperBoxRefreshUrl() {
        return `${apiHostUrl}posts/get-scrapper-info/`;
      }
    },

    methods: {
      loadPosts(url, reset=false) {
        if (reset)
          this.posts = []
        if (url)
          this.axios
            .get(url)
            .then((response) => {
              if (response.data.results) {
                this.posts.push(...response.data.results);
                this.nextUrl = response.data.next;
              } 
            })
            .catch((error) => {
              this.$store.dispatch('setFetchingActive', true);
            });
      },

      searchPosts() {
        let url = this.search ? `${this.url}?search=${this.search}` : this.url
        this.axios
          .get(url)
          .then((response) => {
            if (response.data.results) {
              this.posts = response.data.results;
              this.nextUrl = response.data.next;
            }
          })
          .catch((error) => {
            this.$store.dispatch('setFetchingActive', true);
          });
      },

      handleScroll({ target: { documentElement: { scrollTop, clientHeight, scrollHeight } } }) {
        if (scrollTop + clientHeight >= scrollHeight)
          this.loadPosts(this.nextUrl);
      }
    },

    mounted () {
      this.loadPosts(this.url);
      this.handleDebouncedScroll = debounce(this.handleScroll, 100);
      window.addEventListener('scroll', this.handleDebouncedScroll);
    },

    unmounted () {
      window.removeEventListener('scroll', this.handleDebouncedScroll);
    },

    watch: {
      fetchingActive: function(newVal, oldVal) {
        if (newVal) {
         this.refreshIntervalId = setInterval(this.refresh, 5000);
        } else if (oldVal !== newVal) {
          clearInterval(this.refreshIntervalId);
          this.loadPosts(this.url, true);
        }
      }
    }
  }
</script>

<style lang="sass">
body
  font-family: $font-stack
  font-size: 10pt
  color: $primary-font-color

.flexCol
  display: flex
  flex-direction: column

.btn
  color: $mint-blue 
  background-color: $btn-active
  border: 1px solid $mint-blue 
  border-radius: 5px

.btn:hover
  box-shadow: 1px 2px $mint-blue 
  background-color: $hackernews-grey
  cursor: pointer

.btn:disabled
  box-shadow: 1px 2px Black 
  background-color: $btn-disabled
  cursor: auto
  color: Black
  border: 1px solid Black
</style>

<style module lang="sass">
.container
  display: grid
  grid-template-areas: ". taskInfo ." ". header ." ". content ." ". footer ."
  grid-template-rows: 70px 32px 1fr 32px
  grid-template-columns: 5% 1fr 5%
  padding: 5px
  height: 100vh

.header
  display: grid
  grid-auto-flow: column
  grid-template-columns: 50% 50%
  padding: 0.3rem
  grid-area: header
  background-color: $hackernews-orange
  color: $secondary-font-color
  font-weight: bold

.content
  grid-area: content
  display: flex
  flex-direction: column
  background-color: $hackernews-grey

.footer
  display: flex
  flex-direction: row
  grid-area: footer
  align-items: center
  justify-content: center

.taskInfo
  grid-area: taskInfo
  display: grid
  grid-template-areas: ". apiUpdateBox scrapperUpdateBox"
  grid-gap: 20px
  grid-template-columns: 1fr 300px 300px 
  grid-template-rows: 1fr

.headerGroup
  display: flex
  justify-content: flex-end

.headerGroup *
  margin-left: 10px

.headerTitle
  cursor: pointer

.search
  border: 1px solid $mint-blue 
  border-radius: 5px
  color: $mint-blue 

.search:focus
  outline: none
  border: 1px solid $mint-blue 
  box-shadow: 0 0 10px $mint-blue 

.message
  display: inline-flex
  align-items: center
  justify-content: center
</style>
