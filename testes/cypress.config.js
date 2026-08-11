import { defineConfig } from "cypress";
import allureWriter from "@shelex/cypress-allure-plugin/writer.js";
import { cloudPlugin } from "cypress-cloud/plugin";
import dotenv from "dotenv";
import cucumber from "cypress-cucumber-preprocessor";
import preprocessor from "@cypress/webpack-preprocessor";

dotenv.config();

const envKeys = [
  "API_URL",
  "API_KEY",
  "API_KEY_HEADER",

  "CODIGO_ALUNO",
  "CODIGO_ALUNO_NECESSIDADE",

  "ANO_LETIVO",
  "ANO_TURMA",

  "CODIGO_TURMA",
  "CODIGO_UE",
  "DRE_CODIGO",

  "DATA_REFERENCIA",

  "CPF_RESPONSAVEL",
  "CODIGO_ESCOLA",

  "CODIGO_ALUNO_INEXISTENTE_TURMAS",
  "CODIGO_ALUNO_INEXISTENTE_TURMAS_ANO_LETIVO",
  "ANO_LETIVO_SEM_MATRICULADOS",
  "AUTOCOMPLETE_ALUNO_NOME",
  "AUTOCOMPLETE_LIMITE",

  "CODIGO_ALUNO_SEM_ALTERACAO",
  "CPF_RESPONSAVEL_SEM_ALTERACAO",
  "EMAIL_RESPONSAVEL_SEM_ALTERACAO",
  "NOME_RESPONSAVEL_SEM_ALTERACAO",
  "DDD_SEM_ALTERACAO",
  "NUMERO_CELULAR_SEM_ALTERACAO",
  "NUMERO_RESIDENCIAL_SEM_ALTERACAO",
  "NUMERO_COMERCIAL_SEM_ALTERACAO",
  "DATA_NASCIMENTO_SEM_ALTERACAO",
  "DATA_ATUALIZACAO_SEM_ALTERACAO",
];

export default defineConfig({
  e2e: {
    watchForFileChanges: true,

    supportFile: "cypress/support/e2e.js",

    viewportWidth: 1920,
    viewportHeight: 1080,

    video: false,

    retries: {
      runMode: 2,
      openMode: 0,
    },

    screenshotOnRunFailure: false,
    chromeWebSecurity: false,
    experimentalRunAllSpecs: true,
    failOnStatusCode: false,

    specPattern: ["cypress/e2e/**/*.feature"],

    defaultCommandTimeout: 60000,
    requestTimeout: 60000,
    execTimeout: 60000,
    pageLoadTimeout: 60000,

    env: {
      allure: true,

      // IGNORA TAGS @ignore
      TAGS: "not @ignore",
    },

    async setupNodeEvents(on, config) {
      allureWriter(on, config);

      config.env.allure = true;

      const webpackConfig = {
        module: {
          rules: [
            {
              test: /\.js$/,
              exclude: [/node_modules/],
              use: {
                loader: "babel-loader",
                options: {
                  plugins: ["@babel/plugin-transform-modules-commonjs"],
                },
              },
            },
          ],
        },
      };

      on(
        "file:preprocessor",
        preprocessor({
          webpackOptions: webpackConfig,
        }),
      );

      on("file:preprocessor", cucumber.default());

      const customVariable = Object.fromEntries(
        envKeys.map((key) => [key, process.env[key] ?? ""]),
      );

      config.env = {
        ...config.env,
        ...customVariable,
      };

      if (!config.env.API_URL) {
        throw new Error("API_URL não definida no .env");
      }

      if (!config.env.API_KEY) {
        throw new Error("API_KEY não definida no .env");
      }

      return await cloudPlugin(on, config);
    },
  },
});
