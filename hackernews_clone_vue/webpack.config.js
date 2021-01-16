const webpack = require('webpack');
const path = require('path');
const { VueLoaderPlugin } = require('vue-loader');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = (env, argv) => {

  const dotenv = require('dotenv').config( {
    path: path.join(__dirname, `.env.${env.NODE_ENV}`)
  } );

  apiHostUrl = JSON.stringify(dotenv.parsed.API_HOST_URL);

  config = {
    mode: env.NODE_ENV === 'dev' ? 'development' : 'production',
    entry: [
      './src/main.js'
    ],
    output: {
      path: path.join(__dirname, 'dist'),
      filename: '[name]-[contenthash].js',
    },
    devtool: 'eval-source-map',
    devServer: {
      // Standard output
      stats: 'normal',
      // Automatically adds HotModuleReplacementPlugin for hot reloading 
      hot: true,
      // Shows a full-screen overlay in the browser
      overlay: true,
      // To be accessible externally
      host: '0.0.0.0',
      port: '8080',
      //public: '0.0.0.0:8080', 
    },
    optimization: {
      // when the order of resolving is changed, the IDs will be changed as well
      // with deterministic option, despite any new local dependencies,
      // our vendor hash should stay consistent between builds
      moduleIds: 'deterministic',
      runtimeChunk: 'single',
      splitChunks: {
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
          }
        }
      },
    },
    module: {
      rules: [
        {
          test: /\.vue$/,
          loader: 'vue-loader'
        },
        {
          test: /\.js$/,
          loader: 'babel-loader',
          exclude: /node_modules/,
        },
        {
          test: /\.sass$/,
          oneOf: [
            {
              resourceQuery: /module/,
              use: [
                'style-loader',
                {
                  loader: 'css-loader',
                  options: {
                    modules: {
                      localIdentName: '[path][name]__[local]'
                    },
                  },
                },
                {
                  loader: 'sass-loader',
                  options: {
                    // use dart-sass :default
                    implementation: require("sass"),
                    additionalData: '@use "_variables" as *',
                    sassOptions: {
                      indentedSyntax: true,
                      includePaths: [path.resolve(__dirname, 'src/assets/sass')],
                    },
                  },
                },
              ]
            },
            // this matches plain `<style>` or `<style scoped>`
            {
              use: [
                'style-loader',
                'css-loader',
                {
                  loader: 'sass-loader',
                  options: {
                    // use dart-sass :default
                    implementation: require("sass"),
                    additionalData: '@use "assets/sass/_variables" as *',
                    sassOptions: {
                      indentedSyntax: true,
                      includePaths: [path.resolve(__dirname, 'src')],
                    },
                  },
                },
              ]
            },
          ]
        },
      ],
    },
    plugins: [
      new CleanWebpackPlugin(),
      new VueLoaderPlugin(),
      // Instead of hardcoding JS bundle into index.html, inject it so that HMR works
      new HtmlWebpackPlugin({
        filename: 'index.html',
        template: 'index.html',
        inject: true
      }),
      new webpack.DefinePlugin({
        __API_HOST_URL__: apiHostUrl, 
      }),
    ]
  }

  return config;
};
