import assert from "node:assert/strict";
import test from "node:test";

import {
    buildRetrievalQuery,
} from "./core.js";


test(
    "buildRetrievalQuery combines configured query and player input",
    () => {
        const result = buildRetrievalQuery(
            "Estado actual de la campaña.",
            "Abro la puerta.",
        );

        assert.equal(
            result,
            [
                "Estado actual de la campaña.",
                "",
                "Acción actual del jugador:",
                "Abro la puerta.",
            ].join("\n"),
        );
    },
);


test(
    "buildRetrievalQuery trims both values",
    () => {
        const result = buildRetrievalQuery(
            "  Estado actual.  ",
            "  Abro la puerta.  ",
        );

        assert.equal(
            result,
            [
                "Estado actual.",
                "",
                "Acción actual del jugador:",
                "Abro la puerta.",
            ].join("\n"),
        );
    },
);


test(
    "buildRetrievalQuery returns empty string without configured query",
    () => {
        assert.equal(
            buildRetrievalQuery(
                "   ",
                "Abro la puerta.",
            ),
            "",
        );
    },
);


test(
    "buildRetrievalQuery returns empty string without player input",
    () => {
        assert.equal(
            buildRetrievalQuery(
                "Estado actual.",
                "   ",
            ),
            "",
        );
    },
);