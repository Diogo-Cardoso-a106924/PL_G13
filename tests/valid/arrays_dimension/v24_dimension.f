program arrtest
  integer i, soma
  dimension nums(5)
  soma = 0
  do 10 i = 1, 5
    read *, nums(i)
    soma = soma + nums(i)
10 continue
  print *, soma
end
