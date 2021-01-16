export default {
  toLocal(time) {
    if (time && time !== 'Failed')
      return new Date(time).toLocaleString();
    else
      return time
  }
}
