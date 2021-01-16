<template>
  <div :class="$style.row">
    <div :class="$style.post">
      <div :class="$style.rank">{{ post.rank }}.</div>
      <div :class="$style.title">
        <a href="{{ post.url }}" :class="$style.subject">{{ post.subject }}</a>
      </div>
      <div :class="$style.sentiment">
        <span>Sentiment:</span>
        <span>{{ post.sentiment_label }}</span>
        <span v-if="post.sentiment_score">| {{ post.sentiment_score }}</span>
      </div>
      <div :class="$style.footer">
        <span v-if="post.score">{{ post.score }} points</span>
        <span v-if="post.submitted_by">by {{ post.submitted_by }}</span>
        <span>{{ post.age }}</span>
        <span v-if="post.num_of_comments">| {{ post.num_of_comments }} comments</span>
      </div>
    </div>
  </div>
</template>

<script>
  export default {
    props: ['post', 'fetchingActive', 'message'],
  }
</script>

<style module lang="sass">
.row
  display: flex
  flex-flow: row wrap
  justify-content: flex-start
  margin: 0.3rem

.post
  display: grid
  grid-template-areas: "rank title" ". footer" ". sentiment"
  grid-template-columns: minmax(5px, 33px) 1fr

.rank
  grid-area: rank
  margin-right: 0.1rem

.title
  grid-area: title

.title > span
  margin-right: 0.3rem

.footer 
  grid-area: footer
  display: flex
  flex-direction: row
  justify-content: flex-start

.footer > span
  margin-right: 0.3rem

.sentiment
  grid-area: sentiment
  display: flex
  flex-direction: row
  justify-content: flex-start

.sentiment > span
  margin-right: 0.3rem

.subject
  color: $secondary-font-color 

</style>
