module isolated_module (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] data_in,
    output logic [7:0] data_out
);
    (* preserve *) logic [7:0] state;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= 8'h01;
        else
            state <= {state[6:0], state[7] ^ state[5]} ^ data_in;
    end

    assign data_out = state;
endmodule

module non_isolated_module (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] data_in,
    output logic [7:0] data_out
);
    (* preserve *) logic [7:0] accumulator;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            accumulator <= '0;
        else
            accumulator <= accumulator + data_in;
    end

    assign data_out = accumulator;
endmodule

module top (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [7:0] data_in,
    output logic [7:0] data_out
);
    (* preserve *) logic [7:0] isolated_data;
    (* preserve *) logic [7:0] non_isolated_data;

    isolated_module u_isolated (
        .clk      (clk),
        .rst_n    (rst_n),
        .data_in  (data_in),
        .data_out (isolated_data)
    );

    non_isolated_module u_non_isolated (
        .clk      (clk),
        .rst_n    (rst_n),
        .data_in  (isolated_data),
        .data_out (non_isolated_data)
    );

    assign data_out = non_isolated_data;
endmodule
