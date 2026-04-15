module.exports = {
  apps: [
    {
      name: "universal-dyeing",
      script: "node_modules/tsx/dist/cli.mjs",
      args: "server.ts",
      env: {
        NODE_ENV: "production",
        PORT: 3000
      }
    }
  ]
};
